"""Model zoo — one uniform fitter interface over every clustering family we benchmark.

`src/model_stress_test.py` is the harness; this module is the library it drives. Everything here
speaks the same contract so the harness can treat nine very different algorithms identically:

    fit(train_df, k, test_df=None, spec=DEFAULT_SPEC) -> Fit(labels, labels_test, score, ...)

Families covered (why each is in the ring):

  • **LCA** (`stepmix`) — incumbent refinement layer; model-based on binned categoricals, BIC-selectable.
  • **GMM full / diag** (`sklearn`) — the *continuous* model-based counterpart to LCA. Full covariance
    lets clusters be correlated ellipsoids; diag is the constrained cross-check. Both BIC-selectable,
    both give soft posteriors → a natural confidence/"Unassigned" rule.
  • **k-prototypes / k-modes** (`kmodes`) — hard-centroid mixed-type distance methods (prior cross-check).
  • **SVD+KMeans** — LSA-style: truncated SVD of the one-hot matrix, row-normalised, then KMeans.
    The scalable stand-in for spectral clustering (works at 22M rows; the real thing does not).
  • **Spectral(Gower)** — the genuine article on a small sample: SpectralClustering on a precomputed
    Gower affinity. Finds non-convex clusters a centroid method cannot. O(n²) → capped.
  • **SVC (Support Vector Clustering, Ben-Hur et al. 2001)** — a one-class SVM traces a tight contour
    around the data in kernel space; clusters are the connected components of that contour's
    pre-image. Its k *emerges* from the kernel width, so it can answer "how many blobs are there?"
    without being told. Adjacency is tested over a k-NN graph (the standard speedup) rather than all
    O(n²) pairs. Bounded support vectors are the natural outlier set.
  • **TDA-Mapper** (`kmapper`) — topological: cover a 2-D lens, cluster within each patch, glue the
    patches into a graph, then cut the graph into k communities. Sees flares/loops/continua that
    centroid and mixture methods flatten.
  • **KMeans** — the naive baseline every method must beat to justify itself.

Also here, because they are shared instruments rather than methods:

  • `gower` / `gower_sil` — mixed-type distance + separation metric (Euclidean-on-one-hots lies).
  • `svm_probe` — held-out SVM accuracy at predicting a solution's *own* labels. Reads as
    "are these clusters a learnable region, or an arbitrary cut?" — but see the docstring: a
    geometric partition of a continuum scores ~1.0 here *by construction*, so it is only meaningful
    read alongside the Gower silhouette.
  • `persistence_summary` — H0/H1 persistent homology (`ripser`) on the Gower matrix: an
    algorithm-independent verdict on whether the data is separable blobs, one blob, or has loops.

Read-only. No I/O beyond reading the booking Parquet.
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from kmodes.kmodes import KModes
from kmodes.kprototypes import KPrototypes
from sklearn.cluster import KMeans, SpectralClustering
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import balanced_accuracy_score, f1_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import Normalizer, OneHotEncoder, StandardScaler
from sklearn.svm import SVC, LinearSVC, OneClassSVM
from stepmix.stepmix import StepMix

ROOT = Path(__file__).resolve().parents[1]
BOOKING = ROOT / "data" / "interim" / "pal_features_booking.parquet"

SEED = 42

# Same feature set as src/cluster_diagnostic.py and src/kproto_compare.py, so every number here
# extends the 2026-07-23 / 2026-07-27 decisions instead of re-deriving them on different inputs.
NUMERIC = ("lead_days", "value_tier", "log_rev", "n_coupons")
BINARY = ("round_trip", "foreign_issue", "is_group", "connecting", "peak_month", "corp_channel")
NOMINAL = ("dest_region",)


@dataclass(frozen=True)
class Spec:
    """Which columns play which role. Sub-segment runs pass a narrower spec (constants dropped)."""

    numeric: tuple[str, ...] = NUMERIC
    binary: tuple[str, ...] = BINARY
    nominal: tuple[str, ...] = NOMINAL

    @property
    def cats(self) -> list[str]:
        return list(self.binary) + list(self.nominal)

    @property
    def all_cols(self) -> list[str]:
        return list(self.numeric) + self.cats

    def drop(self, col: str) -> Spec:
        """Leave-one-feature-out variant (used by the feature-dropout stress axis)."""
        return Spec(
            numeric=tuple(c for c in self.numeric if c != col),
            binary=tuple(c for c in self.binary if c != col),
            nominal=tuple(c for c in self.nominal if c != col),
        )


DEFAULT_SPEC = Spec()


@dataclass
class Fit:
    """What every fitter returns."""

    labels: np.ndarray  # labels for the rows it was fitted on
    labels_test: np.ndarray | None = None  # inductive labels for `test_df`, if given
    score: float = float("nan")  # the method's own criterion (BIC / cost / inertia)
    score_name: str = ""
    secs: float = 0.0
    notes: dict = field(default_factory=dict)  # e.g. the gamma SVC settled on, outlier share


# ── data ────────────────────────────────────────────────────────────────────────
def load_sample(n: int, where: str = "", seed: int = SEED) -> pd.DataFrame:
    """Reservoir sample of the booking-grain feature table, with the engineered numerics applied.

    ⚠️ **The filter must be applied in a subquery, below the sample.** Written flat as
    `FROM t {where} USING SAMPLE n ROWS`, DuckDB places `RESERVOIR_SAMPLE` *underneath* `FILTER` in the
    plan: it samples n rows from the whole table and only then filters, so a caller passing a `where`
    silently receives `n x selectivity` rows. Measured 18 Aug 2026 — `where proxy_segment='Corporate'`
    (5.1% of the book) returned **2,077 of 40,000**, and `validate_temporal`'s 12-month windows (~44%)
    returned ~13,000 of 30,000. Deterministic, so it never looked broken. Verify with `EXPLAIN` before
    changing this.
    """
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    df = con.execute(f"""
        SELECT lead_days, max_tier AS value_tier, rev_pos, n_coupons,
               coalesce(dest_region, 'Domestic') AS dest_region,
               round_trip::INT round_trip, foreign_issue::INT foreign_issue,
               is_group::INT is_group, connecting::INT connecting,
               peak_month::INT peak_month, corp_channel::INT corp_channel,
               proxy_segment
        FROM (SELECT * FROM read_parquet('{BOOKING}') {where})
        USING SAMPLE {n} ROWS (reservoir, {seed})
    """).fetchdf()
    df["lead_days"] = df["lead_days"].clip(0, 365)
    df["value_tier"] = df["value_tier"].fillna(df["value_tier"].median())
    df["log_rev"] = np.log1p(df["rev_pos"].clip(lower=0))
    df["n_coupons"] = df["n_coupons"].clip(1, 8)
    return df.reset_index(drop=True)


# ── encodings ───────────────────────────────────────────────────────────────────
def to_codes(df: pd.DataFrame, spec: Spec = DEFAULT_SPEC) -> pd.DataFrame:
    """All features → integer codes (numerics binned). The input LCA and k-modes share."""
    out = pd.DataFrame(index=df.index)
    if "lead_days" in spec.numeric:
        out["lead_bucket"] = pd.cut(df["lead_days"], [-1, 3, 14, 45, 120, 999], labels=False)
    if "value_tier" in spec.numeric:
        out["value_tier"] = df["value_tier"].round().astype(int) - 1
    if "log_rev" in spec.numeric:
        out["rev_bucket"] = pd.qcut(df["log_rev"].rank(method="first"), 5, labels=False)
    if "n_coupons" in spec.numeric:
        out["n_coupons_b"] = np.clip(df["n_coupons"] - 1, 0, 3)
    for c in spec.nominal:
        out[c] = df[c].astype("category").cat.codes
    for b in spec.binary:
        out[b] = df[b].astype(int)
    keep = [c for c in out.columns if out[c].nunique() > 1]  # drop constants (within-parent runs)
    return out[keep].astype(int)


def mixed_matrix(
    df: pd.DataFrame, spec: Spec = DEFAULT_SPEC, scaler: StandardScaler | None = None
) -> tuple[np.ndarray, list[int], StandardScaler]:
    """k-prototypes input: standardised numerics + raw categoricals in one object array."""
    if scaler is None:
        scaler = StandardScaler().fit(df[list(spec.numeric)])
    num = scaler.transform(df[list(spec.numeric)])
    cat = df[spec.cats].astype(str).to_numpy()
    X = np.concatenate([num, cat], axis=1).astype(object)
    return X, list(range(len(spec.numeric), len(spec.numeric) + len(spec.cats))), scaler


@dataclass
class NumEncoder:
    """Numeric design matrix: standardised continuous + binaries left at {0,1} + one-hot nominals.

    Binaries are deliberately *not* standardised — same mixed-type scaling rule as
    `docs/methodology.md` Stage P4, so a rare flag does not get blown up into a dominant axis.
    Nominals drop the first level so GMM's full covariance is not structurally singular.
    """

    spec: Spec = DEFAULT_SPEC
    scaler: StandardScaler | None = None
    ohe: OneHotEncoder | None = None

    def fit(self, df: pd.DataFrame) -> NumEncoder:
        self.scaler = StandardScaler().fit(df[list(self.spec.numeric)])
        if self.spec.nominal:
            self.ohe = OneHotEncoder(
                drop="first", handle_unknown="ignore", sparse_output=False
            ).fit(df[list(self.spec.nominal)].astype(str))
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        parts = [self.scaler.transform(df[list(self.spec.numeric)])]
        if self.spec.binary:
            parts.append(df[list(self.spec.binary)].astype(float).to_numpy())
        if self.ohe is not None:
            parts.append(self.ohe.transform(df[list(self.spec.nominal)].astype(str)))
        return np.concatenate(parts, axis=1).astype(np.float64)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        return self.fit(df).transform(df)


# ── Gower distance (the only separation metric that respects mixed types) ────────
def gower(df: pd.DataFrame, spec: Spec = DEFAULT_SPEC) -> np.ndarray:
    """Gower dissimilarity: range-normalised |diff| on numerics, 0/1 mismatch on categoricals."""
    n = len(df)
    acc = np.zeros((n, n), dtype=np.float32)
    for c in spec.numeric:
        v = df[c].to_numpy(dtype=np.float32)
        rng = float(v.max() - v.min()) or 1.0
        acc += np.abs(v[:, None] - v[None, :]) / rng
    for c in spec.cats:
        v = df[c].astype(str).to_numpy()
        acc += (v[:, None] != v[None, :]).astype(np.float32)
    return acc / len(spec.all_cols)


def gower_cross(a: pd.DataFrame, b: pd.DataFrame, spec: Spec = DEFAULT_SPEC) -> np.ndarray:
    """Gower distances from every row of `b` to every row of `a` → shape (len(b), len(a))."""
    acc = np.zeros((len(b), len(a)), dtype=np.float32)
    for c in spec.numeric:
        va = a[c].to_numpy(dtype=np.float32)
        vb = b[c].to_numpy(dtype=np.float32)
        rng = float(max(va.max(), vb.max()) - min(va.min(), vb.min())) or 1.0
        acc += np.abs(vb[:, None] - va[None, :]) / rng
    for c in spec.cats:
        va = a[c].astype(str).to_numpy()
        vb = b[c].astype(str).to_numpy()
        acc += (vb[:, None] != va[None, :]).astype(np.float32)
    return acc / len(spec.all_cols)


def gower_sil(dist: np.ndarray, labels: np.ndarray) -> float:
    """Silhouette on a precomputed Gower matrix; nan if the solution collapsed to one cluster."""
    lab = np.asarray(labels)
    if len(np.unique(lab[lab >= 0])) < 2:
        return float("nan")
    mask = lab >= 0  # ignore the noise/unassigned label so it is not scored as a cluster
    if mask.sum() < 10:
        return float("nan")
    d = dist[np.ix_(mask, mask)]
    return round(float(silhouette_score(d, lab[mask], metric="precomputed")), 3)


def _knn_extend_gower(
    train: pd.DataFrame, labels: np.ndarray, test: pd.DataFrame, spec: Spec, n_neighbors: int = 10
) -> np.ndarray:
    """Out-of-sample labels for transductive methods: majority vote of the 10 nearest train rows.

    Spectral clustering, Mapper and SVC have no native `predict`. A k-NN extension in the *same*
    distance the method used is the standard way to score held-out rows, and keeps the split-half
    stability test comparable across methods (documented in the report — it is an approximation).
    """
    d = gower_cross(train, test, spec)  # (n_test, n_train)
    idx = np.argpartition(d, min(n_neighbors, d.shape[1] - 1), axis=1)[:, :n_neighbors]
    neigh = labels[idx]
    return np.array(
        [np.bincount(row[row >= 0] + 1).argmax() - 1 if (row >= 0).any() else -1 for row in neigh]
    )


# ── fitters ─────────────────────────────────────────────────────────────────────
def _timed(fn):
    """Wrap a fitter so every Fit carries its own wall-clock cost (a benchmark axis in itself)."""

    def inner(*args, **kw) -> Fit:
        t0 = time.time()
        out = fn(*args, **kw)
        out.secs = round(time.time() - t0, 1)
        return out

    return inner


@_timed
def fit_lca(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
    ca = to_codes(a, spec)
    m = StepMix(
        n_components=k,
        measurement="categorical",
        n_init=2,
        random_state=SEED,
        verbose=0,
        progress_bar=False,
    )
    m.fit(ca)
    lb = None
    if b is not None:
        lb = m.predict(to_codes(b, spec)[ca.columns])
    return Fit(m.predict(ca), lb, float(m.bic(ca)), "BIC")


def _fit_gmm(cov: str):
    @_timed
    def inner(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
        enc = NumEncoder(spec)
        Xa = enc.fit_transform(a)
        m = GaussianMixture(
            n_components=k,
            covariance_type=cov,
            n_init=2,
            reg_covar=1e-3,  # one-hot + binary columns are near-degenerate; keeps Σ invertible
            random_state=SEED,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m.fit(Xa)
        la = m.predict(Xa)
        lb = m.predict(enc.transform(b)) if b is not None else None
        # mean max-posterior = how confidently the mixture assigns; <0.6 means overlapping components
        conf = float(m.predict_proba(Xa).max(axis=1).mean())
        return Fit(la, lb, float(m.bic(Xa)), "BIC", notes={"mean_posterior": round(conf, 3)})

    return inner


fit_gmm_full = _fit_gmm("full")
fit_gmm_diag = _fit_gmm("diag")


@_timed
def fit_kproto(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
    Xa, idx, scaler = mixed_matrix(a, spec)
    m = KPrototypes(n_clusters=k, init="Huang", n_init=2, random_state=SEED, n_jobs=1)
    la = m.fit_predict(Xa, categorical=idx)
    lb = None
    if b is not None:
        Xb, _, _ = mixed_matrix(b, spec, scaler=scaler)
        lb = m.predict(Xb, categorical=idx)
    return Fit(la, lb, float(m.cost_), "cost")


@_timed
def fit_kmodes(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
    ca = to_codes(a, spec)
    m = KModes(n_clusters=k, init="Huang", n_init=2, random_state=SEED, n_jobs=1)
    la = m.fit_predict(ca)
    lb = m.predict(to_codes(b, spec)[ca.columns]) if b is not None else None
    return Fit(la, lb, float(m.cost_), "cost")


@_timed
def fit_kmeans(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
    enc = NumEncoder(spec)
    Xa = enc.fit_transform(a)
    m = KMeans(n_clusters=k, n_init=5, random_state=SEED)
    la = m.fit_predict(Xa)
    lb = m.predict(enc.transform(b)) if b is not None else None
    return Fit(la, lb, float(m.inertia_), "inertia")


@_timed
def fit_svd_kmeans(
    a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC
):
    """LSA-style: truncated SVD → row-normalise → KMeans. The scalable spectral stand-in."""
    enc = NumEncoder(spec)
    Xa = enc.fit_transform(a)
    ncomp = min(10, Xa.shape[1] - 1)
    svd = TruncatedSVD(n_components=ncomp, random_state=SEED).fit(Xa)
    norm = Normalizer()
    Ea = norm.fit_transform(svd.transform(Xa))
    m = KMeans(n_clusters=k, n_init=5, random_state=SEED)
    la = m.fit_predict(Ea)
    lb = m.predict(norm.transform(svd.transform(enc.transform(b)))) if b is not None else None
    return Fit(
        la,
        lb,
        float(m.inertia_),
        "inertia",
        notes={"svd_var_explained": round(float(svd.explained_variance_ratio_.sum()), 3)},
    )


@_timed
def fit_spectral(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
    """True spectral clustering on a precomputed Gower affinity. O(n²) memory → harness caps n."""
    d = gower(a, spec)
    sigma = float(np.median(d[d > 0])) or 1.0
    aff = np.exp(-(d**2) / (2 * sigma**2))
    m = SpectralClustering(
        n_clusters=k, affinity="precomputed", assign_labels="kmeans", random_state=SEED, n_init=5
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        la = m.fit_predict(aff)
    lb = _knn_extend_gower(a, la, b, spec) if b is not None else None
    # spectral has no comparable objective; report the normalised-cut cost so the sweep has a column
    cost = _ncut_cost(aff, la)
    return Fit(la, lb, cost, "ncut", notes={"sigma": round(sigma, 4)})


def _ncut_cost(aff: np.ndarray, labels: np.ndarray) -> float:
    """Normalised cut: Σ_c cut(c, rest)/vol(c). Lower = better-separated graph partition."""
    total = 0.0
    for c in np.unique(labels):
        m = labels == c
        vol = float(aff[m].sum())
        cut = float(aff[np.ix_(m, ~m)].sum())
        total += cut / vol if vol else 0.0
    return round(total, 4)


# γ controls how tightly the kernel contour hugs the data, and so how many components appear.
# The grid runs well past the point of fragmentation on purpose: if a dataset only ever yields one
# component until γ is large enough to shatter it into arbitrary shards, that curve *is* the answer.
SVC_GAMMAS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8)
SVC_NU = 0.05


@_timed
def fit_svc(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
    """Support Vector Clustering (Ben-Hur et al. 2001).

    A one-class SVM wraps the data in the tightest RBF-kernel sphere; its pre-image in data space
    is a set of contours. Two points are in the same cluster iff the whole line segment between
    them stays inside a contour. Clusters = connected components of that relation.

    Two deliberate deviations, both standard practice and both reported:
      • Adjacency is only tested along a **k-NN graph** (10 neighbours), not all O(n²) pairs. Distant
        pairs are connected through intermediate neighbours anyway, so components are preserved at a
        fraction of the cost.
      • `k` cannot be requested — it emerges from the kernel width γ. We sweep γ and keep the fit
        whose component count lands nearest the requested `k`, recording the γ actually used.
    """
    enc = NumEncoder(spec)
    Xa = enc.fit_transform(a)
    best = None
    for g in SVC_GAMMAS:
        oc = OneClassSVM(kernel="rbf", gamma=g, nu=SVC_NU).fit(Xa)
        lab, n_out = _svc_components(Xa, oc)
        n_found = len(np.unique(lab[lab >= 0]))
        cand = (abs(n_found - k), -n_found, g, lab, oc, n_out, n_found)
        if best is None or cand[:3] < best[:3]:
            best = cand
    _, _, g, la, oc, n_out, n_found = best
    lb = _knn_extend_gower(a, la, b, spec) if b is not None else None
    return Fit(
        la,
        lb,
        float(np.mean(oc.decision_function(Xa) < 0)),  # outlier share = the "Unassigned" rate
        "outlier_share",
        notes={"gamma": g, "k_emergent": n_found, "outliers_pct": round(100 * n_out / len(Xa), 1)},
    )


def _svc_components(X: np.ndarray, oc: OneClassSVM, n_neighbors: int = 10, m: int = 8):
    """Connected components of the SVC adjacency relation over a k-NN graph. Label -1 = outlier."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from sklearn.neighbors import NearestNeighbors

    n = len(X)
    inside = oc.decision_function(X) >= 0
    nn = NearestNeighbors(n_neighbors=min(n_neighbors + 1, n)).fit(X)
    _, idx = nn.kneighbors(X)
    src = np.repeat(np.arange(n), idx.shape[1] - 1)
    dst = idx[:, 1:].ravel()
    keep = inside[src] & inside[dst]
    src, dst = src[keep], dst[keep]
    if len(src) == 0:
        return np.full(n, -1), int((~inside).sum())
    # sample m interior points per segment; adjacent iff every sample stays inside the contour
    t = np.linspace(0, 1, m + 2)[1:-1]
    ok = np.ones(len(src), dtype=bool)
    for w in t:
        pts = (1 - w) * X[src] + w * X[dst]
        ok &= oc.decision_function(pts) >= 0
    src, dst = src[ok], dst[ok]
    graph = coo_matrix((np.ones(len(src)), (src, dst)), shape=(n, n))
    _, comp = connected_components(graph, directed=False)
    lab = np.where(inside, comp, -1)
    # relabel interior components densely, and drop singleton components into the outlier bucket
    out = np.full(n, -1)
    next_id = 0
    for c in np.unique(lab[lab >= 0]):
        mask = lab == c
        if mask.sum() < max(10, 0.001 * n):
            continue
        out[mask] = next_id
        next_id += 1
    return out, int((out < 0).sum())


MAPPER_CUBES = 10
MAPPER_OVERLAP = 0.35


@_timed
def fit_mapper(a: pd.DataFrame, k: int, b: pd.DataFrame | None = None, spec: Spec = DEFAULT_SPEC):
    """TDA Mapper (`kmapper`): 2-D SVD lens → overlapping cover → per-patch clustering → graph.

    The graph's shape *is* the finding: a single long chain means a continuum, disjoint blobs mean
    real segments, a loop means cyclical structure. To land in the benchmark alongside k-honouring
    methods, the node graph is cut into `k` communities and each row takes the community of the node
    it belongs to (majority vote when nodes overlap). Rows in no node — Mapper's own boundary set —
    stay -1.

    The cut is **Ward agglomerative on node centroids under the Mapper graph as a connectivity
    constraint**, not spectral on the raw adjacency. Spectral was tried first and is the wrong tool
    here: this graph is one giant component plus a scatter of isolated nodes, so the eigenvectors
    peel off the isolated nodes one at a time and hand back 99% of the rows in a single community —
    an artefact of the graph's connectivity, not a segmentation. Clustering the node *centroids*
    subject to graph adjacency keeps communities both feature-meaningful and topologically
    contiguous, which is what Mapper is for.
    """
    import kmapper as km
    from scipy.sparse import csr_matrix
    from sklearn.cluster import AgglomerativeClustering

    enc = NumEncoder(spec)
    Xa = enc.fit_transform(a)
    mapper = km.KeplerMapper(verbose=0)
    lens = mapper.fit_transform(Xa, projection=TruncatedSVD(n_components=2, random_state=SEED))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        graph = mapper.map(
            lens,
            Xa,
            cover=km.Cover(n_cubes=MAPPER_CUBES, perc_overlap=MAPPER_OVERLAP),
            clusterer=AgglomerativeClustering(n_clusters=2, linkage="ward"),
        )
    nodes = list(graph["nodes"].items())
    if not nodes:
        return Fit(np.full(len(a), -1), None, float("nan"), "n_nodes")
    node_ids = [nid for nid, _ in nodes]
    pos = {nid: i for i, nid in enumerate(node_ids)}
    nn = len(node_ids)

    # node adjacency = shared membership (Mapper's links, plus overlap weight)
    adj = np.zeros((nn, nn))
    for src, dsts in graph["links"].items():
        for dst in dsts:
            if src in pos and dst in pos:
                adj[pos[src], pos[dst]] = adj[pos[dst], pos[src]] = 1.0
    from scipy.sparse.csgraph import connected_components as _cc

    n_components = _cc(adj, directed=False)[0]

    # cut the node graph into k communities: Ward on node centroids, constrained by adjacency
    if nn <= k:
        comm = np.arange(nn)
    else:
        centroids = np.vstack([Xa[np.asarray(mem, dtype=int)].mean(axis=0) for _, mem in nodes])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # sklearn warns when it has to bridge components
            comm = AgglomerativeClustering(
                n_clusters=k, linkage="ward", connectivity=csr_matrix(adj)
            ).fit_predict(centroids)

    votes = np.zeros((len(a), max(int(comm.max()) + 1, 1)))
    for nid, members in nodes:
        votes[np.asarray(members, dtype=int), comm[pos[nid]]] += 1
    covered = votes.sum(axis=1) > 0
    la = np.where(covered, votes.argmax(axis=1), -1)
    lb = _knn_extend_gower(a, la, b, spec) if b is not None else None
    return Fit(
        la,
        lb,
        float(nn),
        "n_nodes",
        notes={
            "n_nodes": nn,
            "graph_components": int(n_components),
            "uncovered_pct": round(100 * float((~covered).mean()), 1),
        },
    )


@dataclass(frozen=True)
class Method:
    fit: object
    score_name: str
    lower_better: bool
    max_n: int | None = None  # O(n²)+ methods are capped; the harness reports n_used
    honours_k: bool = True
    family: str = ""


METHODS: dict[str, Method] = {
    "LCA": Method(fit_lca, "BIC", True, family="mixture (categorical)"),
    "GMM(full)": Method(fit_gmm_full, "BIC", True, family="mixture (Gaussian)"),
    "GMM(diag)": Method(fit_gmm_diag, "BIC", True, family="mixture (Gaussian)"),
    "k-prototypes": Method(fit_kproto, "cost", True, family="centroid (mixed)"),
    "k-modes": Method(fit_kmodes, "cost", True, family="centroid (categorical)"),
    "KMeans": Method(fit_kmeans, "inertia", True, family="centroid (Euclidean)"),
    "SVD+KMeans": Method(fit_svd_kmeans, "inertia", True, family="spectral (scalable)"),
    "Spectral(Gower)": Method(fit_spectral, "ncut", True, max_n=4_000, family="spectral (exact)"),
    "SVC": Method(fit_svc, "outlier_share", True, max_n=3_000, honours_k=False, family="kernel"),
    # Mapper's graph is emergent, but cutting the node graph into k communities lets it compete
    # head-to-head with the k-honouring methods; `graph_components` reports the emergent count.
    "TDA-Mapper": Method(fit_mapper, "n_nodes", False, max_n=8_000, family="topological"),
}


# ── the SVM separability probe ──────────────────────────────────────────────────
def svm_probe(
    df: pd.DataFrame, labels: np.ndarray, spec: Spec = DEFAULT_SPEC, n: int = 6_000
) -> dict:
    """Held-out SVM accuracy at predicting a clustering's *own* labels.

    Reads as "is this partition a learnable, deployable region of feature space?" — which matters,
    because a segmentation you cannot re-derive from the features cannot be scored on new bookings.

    **Read it with the Gower silhouette, never alone.** A KMeans cut of a featureless continuum is
    linearly separable *by construction* and scores ≈1.0 here while having ≈0 real separation. The
    informative combination is high probe **and** high silhouette; high probe with low silhouette is
    the signature of an arbitrary geometric slice. `gap_vs_shuffled` guards the other direction: the
    same probe trained on shuffled labels, so a near-zero gap flags a probe that learned nothing.
    """
    lab = np.asarray(labels)
    mask = lab >= 0
    if len(np.unique(lab[mask])) < 2 or mask.sum() < 200:
        return {
            "svm_bal_acc": float("nan"),
            "svm_macro_f1": float("nan"),
            "gap_vs_shuffled": float("nan"),
        }
    d, y = df.loc[mask].reset_index(drop=True), lab[mask]
    if len(d) > n:
        idx = np.random.default_rng(SEED).choice(len(d), n, replace=False)
        d, y = d.iloc[idx].reset_index(drop=True), y[idx]
    X = NumEncoder(spec).fit_transform(d)
    counts = pd.Series(y).value_counts()
    keep = np.isin(y, counts[counts >= 6].index)  # stratified split needs ≥2 per class per side
    X, y = X[keep], y[keep]
    if len(np.unique(y)) < 2:
        return {
            "svm_bal_acc": float("nan"),
            "svm_macro_f1": float("nan"),
            "gap_vs_shuffled": float("nan"),
        }
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=SEED, stratify=y)
    model = SVC(kernel="rbf", C=1.0, cache_size=500) if len(Xtr) <= 4_000 else LinearSVC(C=1.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        rng = np.random.default_rng(SEED)
        shuf = rng.permutation(ytr)
        base = type(model)(**model.get_params()).fit(Xtr, shuf).predict(Xte)
    acc = balanced_accuracy_score(yte, pred)
    return {
        "svm_bal_acc": round(float(acc), 3),
        "svm_macro_f1": round(float(f1_score(yte, pred, average="macro")), 3),
        "gap_vs_shuffled": round(float(acc - balanced_accuracy_score(yte, base)), 3),
    }


# ── persistent homology: an algorithm-independent verdict on the data's shape ────
def persistence_summary(df: pd.DataFrame, spec: Spec = DEFAULT_SPEC, n: int = 800) -> dict:
    """H0/H1 persistent homology (`ripser`) on the Gower distance matrix.

    H0 bars are connected components appearing and merging as the distance threshold grows: **a
    handful of long H0 bars = genuinely separated groups; one long bar and a smooth tail of short
    ones = a continuum**, which is the shape every previous diagnostic inferred indirectly. H1 bars
    are loops — a long H1 bar would mean cyclical structure (e.g. a seasonal/lifecycle cycle) that
    no partitional method can represent at all.

    `n_significant_H0` counts bars longer than the largest gap in the sorted bar lengths — the
    standard gap heuristic for "how many components are real", i.e. a topological estimate of *k*
    that never sees a proxy label.

    High-dimensional point clouds always produce *hundreds* of short-lived H1 bars, so a raw loop
    count means nothing. `H1_max_over_p95` is the discriminator: the longest loop divided by the 95th
    percentile of all loops. Near 1 means the longest loop is indistinguishable from the noise floor
    (no real cycle); a large ratio would mean one genuine cycle standing clear of it.
    """
    from ripser import ripser

    sub = df.sample(min(n, len(df)), random_state=SEED).reset_index(drop=True)
    d = gower(sub, spec).astype(np.float64)
    dgms = ripser(d, distance_matrix=True, maxdim=1)["dgms"]
    h0 = dgms[0][:, 1]
    h0 = np.sort(h0[np.isfinite(h0)])[::-1]
    h1 = dgms[1]
    h1_pers = np.sort(h1[:, 1] - h1[:, 0])[::-1] if len(h1) else np.array([])
    gaps = -np.diff(h0) if len(h0) > 1 else np.array([0.0])
    n_sig = int(np.argmax(gaps) + 1) if len(gaps) else 1
    return {
        "n_rows": len(sub),
        "n_significant_H0": n_sig,
        "top_H0_deaths": [round(float(v), 4) for v in h0[:6]],
        "H0_gap_ratio": round(float(h0[0] / h0[1]), 3) if len(h0) > 1 and h0[1] else float("nan"),
        "n_H1_loops": int(len(h1_pers)),
        "max_H1_persistence": round(float(h1_pers[0]), 4) if len(h1_pers) else 0.0,
        "H1_max_over_p95": (
            round(float(h1_pers[0] / np.percentile(h1_pers, 95)), 3)
            if len(h1_pers) > 20 and np.percentile(h1_pers, 95) > 0
            else float("nan")
        ),
        "H1_over_H0": (round(float(h1_pers[0] / h0[0]), 3) if len(h1_pers) and h0[0] else 0.0),
    }
