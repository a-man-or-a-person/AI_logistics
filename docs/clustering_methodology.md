# Методика исследования Clustering Contract v1

1. Зафиксировать один origin_fias, один destination_region и общий набор
   period/tariff/vehicle/tonnage filters.
2. Агрегировать destination FIAS по trip_count=bid_count; цену и ₽/км считать
   trip-weighted.
3. Сопоставить Delaunay+adaptive pruning и mutual kNN по components, isolates,
   degree и edge-distance audit.
4. На одном и том же graph запустить Geography, Geo+Cost и Bear Zones.
5. Для Geography сравнить Manual K и Auto K; connectivity violations обязаны быть 0.
6. Для Geo+Cost сохранить sensitivity 80/20, 70/30, 60/40 без объявления winner.
7. Для Bear сохранить defaults +35% и singleton +70%; trip_count использовать
   только как economic weight и отображаемый объём, без eligibility threshold.
8. Сравнить только факты: compactness, outliers, rate spread, trip coverage,
   connectedness и slice stability.
9. Для Auto K строить research curve 2…20 и применять Pareto + tiny/complexity
   tie-breaking; search ceiling не может считаться решением без диагностики.
10. Для Geo+Cost сохранять cluster rate list, within MAD/variance, between variance
    и between/within ratio.

Функция ml.experiments.clustering_modes.run_clustering_modes сохраняет единый
clustering_modes.json с reproducibility metadata, graph study и тремя режимами.
K-Means runner сохранён только как legacy baseline.

Polygons, production API и frontend находятся за stop point этого ML milestone.
