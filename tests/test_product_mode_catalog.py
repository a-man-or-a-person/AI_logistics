import pytest

from backend.product_modes import (
    CANONICAL_PRODUCT_MODE_IDS,
    ModeCapabilities,
    ModeDataset,
    ModeOutcome,
    ModeParameterCapability,
    ModePreview,
    ModeSelection,
    PendingProductMode,
    ProductModeCatalog,
    ProductModeNotMigratedError,
    default_product_mode_catalog,
)
from backend.services.clustering_service import ClusteringService
from ml.clustering.base import ClusterPoint, ClusterResult
from ml.spatial.graph import SpatialGraph


def test_default_catalog_has_canonical_modes_and_manifest_order():
    catalog = default_product_mode_catalog()

    assert catalog.mode_ids == (
        "geography",
        "geo_cost",
        "geo_volume",
        "bear_zones",
        "bear_volume_zones",
    )
    assert catalog.mode_ids == CANONICAL_PRODUCT_MODE_IDS
    assert tuple(item.mode_id for item in catalog.manifest()) == catalog.mode_ids


def _registrations(*mode_ids: str) -> tuple[PendingProductMode, ...]:
    return tuple(
        PendingProductMode(
            ModeCapabilities(
                mode_id=mode_id,
                parameters=(),
                semantic_dimensions=("geography",),
                result_kind="partition",
            )
        )
        for mode_id in mode_ids
    )


@pytest.mark.parametrize(
    ("mode_ids", "message"),
    [
        (
            (*CANONICAL_PRODUCT_MODE_IDS[:-1], "bear_zones"),
            "Duplicate Product mode IDs: bear_zones",
        ),
        (CANONICAL_PRODUCT_MODE_IDS[:-1], "Missing Product mode IDs: bear_volume_zones"),
        (
            (*CANONICAL_PRODUCT_MODE_IDS[:-1], "experimental"),
            "Unknown Product mode IDs: experimental",
        ),
        (
            (
                "geo_cost",
                "geography",
                "geo_volume",
                "bear_zones",
                "bear_volume_zones",
            ),
            "Product modes must use canonical order",
        ),
    ],
)
def test_catalog_rejects_invalid_registration(mode_ids, message):
    with pytest.raises(ValueError, match=message):
        ProductModeCatalog(_registrations(*mode_ids))


def test_default_manifest_exposes_deterministic_product_capabilities():
    capabilities = {item.mode_id: item for item in default_product_mode_catalog().manifest()}

    assert tuple(capabilities) == CANONICAL_PRODUCT_MODE_IDS
    assert capabilities["geography"].parameter_names == ("k_mode", "n_clusters")
    assert capabilities["geography"].default_parameters == (
        ("k_mode", "auto"),
        ("n_clusters", "auto"),
    )
    assert capabilities["geography"].semantic_dimensions == ("geography",)
    assert capabilities["geography"].result_kind == "partition"

    assert capabilities["geo_cost"].presets == (
        (("geography_weight", 0.8), ("economics_weight", 0.2)),
        (("geography_weight", 0.7), ("economics_weight", 0.3)),
        (("geography_weight", 0.6), ("economics_weight", 0.4)),
    )
    assert capabilities["geo_volume"].semantic_dimensions == (
        "geography",
        "volume",
    )

    bear = capabilities["bear_zones"]
    assert bear.result_kind == "zones"
    assert bear.parameters[0].choices == (0.2, 0.25, 0.3, 0.35, 0.4, 0.5)
    assert bear.parameters[1].fixed is True
    assert bear.comparison_parameters == bear.default_parameters


def test_capabilities_reject_internally_inconsistent_metadata():
    parameter = ModeParameterCapability("k_mode", "choice", "auto", ("auto", "manual"))

    with pytest.raises(ValueError, match="Duplicate parameter names: k_mode"):
        ModeCapabilities(
            mode_id="geography",
            parameters=(parameter, parameter),
            semantic_dimensions=("geography",),
            result_kind="partition",
        )

    with pytest.raises(ValueError, match="Unknown preset parameters: unknown"):
        ModeCapabilities(
            mode_id="geography",
            parameters=(parameter,),
            semantic_dimensions=("geography",),
            result_kind="partition",
            presets=((("unknown", 1),),),
        )

    with pytest.raises(ValueError, match="Default must be one of the declared choices"):
        ModeParameterCapability("k_mode", "choice", "invalid", ("auto", "manual"))

    with pytest.raises(ValueError, match="Default is outside declared limits"):
        ModeParameterCapability("weight", "number", 2.0, minimum=0.0, maximum=1.0)

    with pytest.raises(ValueError, match="Default is incompatible with parameter kind: number"):
        ModeParameterCapability("weight", "number", "invalid")

    with pytest.raises(ValueError, match="Unsupported preset value for k_mode: invalid"):
        ModeCapabilities(
            mode_id="geography",
            parameters=(parameter,),
            semantic_dimensions=("geography",),
            result_kind="partition",
            presets=((("k_mode", "invalid"),),),
        )

    with pytest.raises(ValueError, match="Unknown semantic dimensions: test"):
        ModeCapabilities(
            mode_id="geography",
            parameters=(parameter,),
            semantic_dimensions=("test",),
            result_kind="partition",
        )


def test_mode_selection_enforces_normalized_constructor_invariants():
    with pytest.raises(ValueError, match="Product mode ID cannot be empty"):
        ModeSelection("", ())

    with pytest.raises(ValueError, match="Mode selection parameter names must be unique"):
        ModeSelection("geography", (("k_mode", "auto"), ("k_mode", "manual")))

    with pytest.raises(ValueError, match="Mode selection parameters must use canonical order"):
        ModeSelection("geography", (("n_clusters", "auto"), ("k_mode", "auto")))


class ExampleGeographyMode:
    def __init__(self, capabilities):
        self.capabilities = capabilities

    def select(self, parameters):
        return ModeSelection.from_mapping(self.capabilities.mode_id, parameters)

    def evaluate(self, selection, dataset, operation):
        if operation == "preview":
            return ModePreview(selection, tuple(point.id for point in dataset.points))
        return ModeOutcome(
            selection,
            "success",
            ClusterResult("example", {}, {"a": 0}, (), (), {}),
        )


def test_catalog_select_and_evaluate_use_the_product_mode_interface():
    registrations = list(_registrations(*CANONICAL_PRODUCT_MODE_IDS))
    registrations[0] = ExampleGeographyMode(registrations[0].capabilities)
    catalog = ProductModeCatalog(tuple(registrations))
    raw_parameters = {"n_clusters": "auto", "k_mode": "auto"}

    selection = catalog.select("geography", raw_parameters)
    raw_parameters["k_mode"] = "manual"
    assert selection.parameters == (("k_mode", "auto"), ("n_clusters", "auto"))

    point = ClusterPoint("a", "A", "Region", 0.0, 0.0)
    graph = SpatialGraph(
        node_ids=("a",),
        edges=(),
        adjacency={"a": frozenset()},
        connected_components=(("a",),),
        isolated_point_ids=("a",),
        method="test",
        parameters={},
        audit={},
    )
    dataset = ModeDataset((point,), graph)

    preview = catalog.evaluate(selection, dataset, "preview")
    outcome = catalog.evaluate(selection, dataset, "run")

    assert preview == ModePreview(selection, ("a",))
    assert outcome.status == "success"
    assert outcome.result.point_assignments == {"a": 0}


def test_default_registrations_cannot_be_used_before_their_migration_ticket():
    catalog = default_product_mode_catalog()

    with pytest.raises(
        ProductModeNotMigratedError,
        match="Product mode has not migrated to the catalog: geography",
    ):
        catalog.select("geography", {})


def test_catalog_rejects_registration_without_product_mode_interface():
    class IncompleteMode:
        capabilities = _registrations("geography")[0].capabilities

    registrations = list(_registrations(*CANONICAL_PRODUCT_MODE_IDS))
    registrations[0] = IncompleteMode()

    with pytest.raises(
        ValueError,
        match="Product mode registration does not implement select/evaluate: geography",
    ):
        ProductModeCatalog(tuple(registrations))


def test_catalog_rejects_registration_without_capabilities_clearly():
    registrations = list(_registrations(*CANONICAL_PRODUCT_MODE_IDS))
    registrations[0] = object()

    with pytest.raises(
        ValueError,
        match="Product mode registration is missing capabilities at index 0",
    ):
        ProductModeCatalog(tuple(registrations))


def test_clustering_service_accepts_catalog_without_using_it_as_runtime_authority():
    catalog = default_product_mode_catalog()

    service = ClusteringService(
        records_factory=lambda: (),
        product_mode_catalog=catalog,
    )

    assert service.product_mode_catalog is catalog
