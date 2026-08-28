# Методика выбора территориальных кластеров

1. Построить forecast-free routes и clustering audit.
2. Получить одну geocoded-точку на destination FIAS.
3. Для каждого `K` прогнать `none` и `shipment_count` с несколькими seeds.
4. Сравнить compactness, shipment balance, coverage и ARI stability.
5. Оставить недоминируемые Pareto-кандидаты; не выбирать `K` только по silhouette.
6. При наличии официальной границы отдельно построить зоны и проверить их QA.

Минимальный запуск:

```powershell
python -m ml.data.clustering_dataset --output-dir reports/clustering_data
python -m ml.data.locations --output-dir reports/locations/region
python -m ml.experiments.clustering_experiment `
  --locations reports/locations/region/locations.json `
  --output-dir reports/clustering/region `
  --k-min 2 --k-max 10 --weight-mode both --stability-runs 5
```

Результат содержит leaderboard, per-run assignments/metrics и
`decision_gate_clustering.json` без price/WAPE-критериев.
