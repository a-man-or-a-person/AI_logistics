# ИИ Логистика — текущая архитектура

> **Статус: CURRENT.** Этот документ описывает только то, что реализовано сейчас. Продуктовые значения и будущий объём принадлежат [CONTEXT.md](../../CONTEXT.md); обзор для обсуждений — [Project Brief](../project/project-brief.md).

## Система

ИИ Логистика — локальное Flask-приложение с браузерным интерфейсом. Текущий Product позволяет выбрать одно направление и срез данных Pulse, запустить один из пяти режимов кластерного анализа и изучить точки, кластеры, показатели качества данных и нейтральное сравнение режимов. Для Geography, Geo+Cost и Geo+Volume результат также включает desktop-таблицу кластеров и ленивую детализацию точки назначения до строк Pulse.

```mermaid
flowchart LR
    User[Логист] --> UI[Product workspace\nбраузер]
    UI --> API[Flask\n/api/clustering/*]
    API --> Service[ClusteringService]
    Service --> Pulse[(Pulse CSV)]
    Service --> Coordinates[(Coordinate cache)]
    Service --> Catalog[ProductModeCatalog\nи пять адаптеров]
    Catalog --> Algorithms[ML clustering algorithms]
    Service --> API
    API --> UI

    Research[RESEARCH\nml/experiments и evaluation] -. отдельный контур .-> Pulse
    User -. совместимость .-> LegacyUI[LEGACY\nData Map]
    LegacyUI --> MapAPI[Legacy map routes]
    LegacyClient[Legacy client] --> LegacyAPI[LEGACY\n/api/ml-cluster]
```

Product использует алгоритмы из `ml/clustering`, но не зависит от исследовательских runner-ов и отчётов. Наличие эксперимента в `ml/experiments` не делает его продуктовой функцией. Data Map и `/api/ml-cluster` сохранены как отдельные совместимые поверхности; канонический Product вызывает `/api/clustering/*`.

## Product runtime flow

NPI-10 добавляет `POST /api/clustering/export`: ClusteringService находит exact saved
result, использует общий frozen-point row access и serializer с detail API, а
`xlsx_export.py` записывает saved table и direction rows в disk-backed XLSX.
Serializer не рассчитывает экономику и не вызывает clustering. Generation validation
заканчивается перед HTTP attachment. NPI-11 добавляет binary-aware frontend transport
и inspector download control; backend остаётся единственным генератором workbook.

```mermaid
flowchart TD
    Form[Frontend: направление, фильтры, режим] --> Options[GET options / origins]
    Options --> Capabilities[Backend mode capabilities]
    Capabilities --> Controls[Frontend renders controls]
    Form --> Request[preview / run / compare]
    Request --> PulseAnalytics[Pulse analytics and filtering]
    PulseAnalytics --> Aggregate[Destination-point aggregation\nexplicit origin set × one destination region]
    Aggregate --> Resolve[Resolve destination coordinates]
    Resolve --> Project[Project resolved points]
    Project --> Graph[Build full SpatialGraph\nfrom geography only]
    Graph --> Dataset[ModeDataset\npoints + full graph + quality]
    Dataset --> Adapter[Selected Product mode adapter]
    Adapter --> Eligibility[Mode eligibility\nand induced subgraph when needed]
    Eligibility --> Algorithm[Clustering algorithm]
    Algorithm --> Projection[Cluster-table projection]
    Projection --> Response[Product result + data snapshot]
    Response --> View[Desktop table + map + inspector]
    Response --> Comparison[Cached comparison switching]
    View --> Detail[POST point-rows\nlazy paginated Pulse detail]
    Detail --> Pulse
```

1. Frontend получает направления, фильтры и машинно-читаемые возможности режимов через Product API. Эти данные определяют доступные контролы и значения; интерфейс не содержит второго независимого каталога возможностей.
2. Frontend выбирает одно или несколько отправлений по FIAS. Backend-запрос фиксирует canonical набор `origin_fiases` (scalar `origin_fias` эквивалентен singleton), один регион назначения и общие типы периода, цены, транспорта и тоннажа. `ClusteringService` объединяет строки Pulse по destination FIAS до coordinates.
3. Сервис сопоставляет агрегированные точки с локальным кэшем координат. Неразрешённые точки остаются в отчёте качества данных, но не передаются пространственному алгоритму.
4. Разрешённые координаты проецируются, после чего сервис строит полный `SpatialGraph` только из пространственных данных. Экономика не создаёт рёбра.
5. Сервис формирует общий `ModeDataset`: точки с доступными признаками, полный граф и сведения о качестве. Выбранный адаптер нормализует параметры, определяет допустимые точки, выбирает полный или индуцированный граф и вызывает алгоритм своего режима.
6. `ClusteringService` проецирует принадлежность точек к фактическим кластерам того же запуска в рассчитанную backend таблицу, не выполняя отдельную кластеризацию. Для Geography, Geo+Cost и Geo+Volume ответ содержит `cluster_table`; Bear Cost и Bear Volume сохраняют прежнее поведение и возвращают `{"supported": false}`.
7. Сервис возвращает Product-результат вместе с `data_snapshot`. Frontend отображает один снимок на desktop-таблице, карте и в inspector. Для выбранной точки он лениво запрашивает страницы строк Pulse через `POST /api/clustering/point-rows`, повторяя замороженные фильтры и снимок; backend проверяет их согласованность перед выдачей данных.

`preview` проходит тот же каталог и правила выбора режима, но не строит граф и не запускает кластеризацию. `compare` берёт фиксированные сравниваемые конфигурации из каталога и выполняет их на одном срезе данных. Полученные варианты и их таблицы сохраняются frontend; переключение режима сравнения использует этот кэш без пересчёта. Backend-результаты, локации и графы также кэшируются в памяти и сбрасываются при изменении исходного файла или кэша координат.

Для нового Calculate/Compare frontend проверяет cache reuse через uncached
`/api/clustering/revision`: существующий metadata generation token и присутствие
exact frozen result в in-memory cache. Проверка делает stat без загрузки Pulse index.
Смена generation инвалидирует старые results/comparisons/summaries/pages; restart
или eviction инвалидирует только недоступные saved results. Frozen map/table
сохраняется до успешного расчёта. Подробный wire contract и пределы fingerprint
зафиксированы в Product v1 contract; алгоритмы и формулы не меняются.

## Владение режимами

`ProductModeCatalog` — упорядоченный реестр ровно пяти Product-режимов. Он проверяет полноту регистрации, публикует capabilities, направляет выбор и выполнение в нужный адаптер. Каталог не реализует смысл конкретного режима.

Каждый адаптер владеет своим внешним продуктовым поведением:

- нормализацией и проверкой параметров;
- семантическими измерениями и видом результата;
- правилами допустимости точек;
- переводом общего `ModeDataset` в параметры алгоритма;
- продуктовыми статусами точек, предупреждениями и состоянием `no_bears`.

`ClusteringService` остаётся нейтральным к конкретным режимам. Он владеет общей инфраструктурой: областью запроса, доступом к Pulse, агрегацией, координатами, проекцией, полным графом, кэшами, качеством данных, наблюдаемостью, `data_snapshot`, расчётом общей кластерной таблицы и общей JSON-формой результата.

Подробные параметры и публичное поведение находятся в [Product v1 contract](../clustering_product_v1_contract.md), а не дублируются здесь.

## Граница графа и допустимости

Главный пространственный инвариант: полный граф строится до бизнес-фильтрации. Это сохраняет единую географическую основу и не позволяет стоимости или объёму создавать соседство.

- Geography получает все точки с координатами, удаляет экономические признаки из алгоритмического ввода и использует полный граф.
- Geo+Volume использует все пространственные точки и полный граф; объём влияет на объединение внутри допустимой пространственной связности.
- Geo+Cost сначала выбирает точки с валидной экономикой, затем берёт их индуцированный подграф полного графа.
- Bear Cost выбирает точки с положительным объёмом и валидным ₽/км, затем использует индуцированный подграф.
- Bear Volume выбирает точки с положительным объёмом, затем использует индуцированный подграф.

Индуцированный подграф может только удалить точки и рёбра полного графа. Поэтому бизнес-признак меняет допустимость и результат, но не создаёт новую пространственную связь.

## Backend и frontend

NPI-09 переиспользует существующий backend medoid/member/coordinate contract без
изменения алгоритмов. Один frontend formatter используется map label и cluster
inspector для одинакового имени/FIAS и unavailable-name состояния. Представитель
остаётся временным географическим ориентиром; новая таблица/семантика Bear не добавлены.

Backend владеет машинными возможностями и расчётами: составом и порядком режимов, параметрами, допустимыми значениями, пресетами, типом результата, поддержкой сравнения, показателями кластерной таблицы и проверкой согласованности детализации. `/api/clustering/options` публикует manifest режимов вместе с доступными значениями фильтров.

Frontend владеет представлением: подписями, компоновкой, состояниями формы и результата, stale-state, сортировкой и отображением рассчитанной таблицы, взаимодействием таблицы, карты и inspector, ленивой загрузкой страниц детализации, а также нейтральными карточками сравнения. Он строит контролы из backend capabilities, но backend не передаёт ему UI-схему или разметку.

HTTP-граница остаётся тонкой: Flask handlers разбирают запрос, назначают или возвращают `X-Request-ID`, вызывают сервис и переводят продуктовые ошибки в стабильный ответ. Результат `run` и каждый режим в `compare` аддитивно содержат `data_snapshot` и `cluster_table`; `POST /api/clustering/point-rows` принимает тот же замороженный срез, снимок, точку и параметры пагинации. Точный API-контракт описан отдельно в [Product v1 contract](../clustering_product_v1_contract.md).

## Данные

Pulse — источник архивных, текущих и уже рассчитанных вне системы прогнозных данных. Система фильтрует и анализирует их; собственный прогноз она не строит. Канонические значения полей и правила агрегации описаны в [data contract](../clustering_data_contract.md).

Текущий Product также использует локальный кэш координат. Покрытие координатами и покрытие перевозок отражаются раздельно. Пропущенная координата исключает точку из пространственного расчёта, но сохраняется в диагностике качества.

`data_snapshot` фиксирует поколения Pulse и кэша координат для результата. Детализация точки принимается только для того же снимка, замороженного контекста фильтров и точки из соответствующего результата; изменение данных требует нового расчёта.

Новый detail-контекст дополнительно связывает canonical origins, mode и
нормализованные parameters с точным result-cache entry и saved membership;
eviction/restart даёт `RESULT_UNAVAILABLE` без rerun. Старый scalar detail сохраняет
slice compatibility. Generation проверяется до публикации caches и завершения
preview/run/compare/detail. Backend regional All разрешает полный набор origins
выбранного региона до segment filters, один раз для compare. Selection intent
сохраняется отдельно от resolved set; detail использует только frozen explicit
set и saved membership, без повторного All resolution. UI включает explicit All
с выбором региона доставки и раскрываемым полным saved набором. Point origin summary
использует тот же frozen-row доступ и существующую valid-weight агрегацию; cluster
attribution берётся из saved point. Inspector выбирает origin и загружает только его
строки, с отдельными result/point/origin cache keys. XLSX download использует exact
saved result/intent/current sort и существующие generation/result rejection helpers;
не вызывает run/compare и не раскрывает All повторно.

## Границы контуров

| Контур | Что ему принадлежит | Что ему не принадлежит |
|---|---|---|
| **Product** | `/api/clustering/*`, пять адаптеров, общий сервис, Product workspace, таблица/карта/inspector/compare и детализация точки | Исследовательские runner-ы, выбор лучшего режима, собственный прогноз |
| **RESEARCH** | Эксперименты, сравнение алгоритмов, устойчивость, чувствительность, evaluation и отчёты | Автоматическое включение результата в Product |
| **LEGACY** | Data Map, `/api/ml-cluster` и сохранённые совместимые интерфейсы | Канонический Product workflow и его ограничения |

Поддерживаемые границы проверяются высокоуровневыми контрактными тестами каталога, Product API и frontend, а режимные тесты фиксируют допустимость и топологию. Этот документ не перечисляет тесты и классы: код и тесты остаются источником точной реализации.

## Куда идти глубже

- [Pulse contract and ATI readiness](../pulse_ati_readiness.md) — проверенные Pulse responsibilities, ограничения source seam и UNKNOWN будущей ATI-интеграции; CURRENT и NEXT разделены.
- [Project Brief](../project/project-brief.md) — короткий обзор Product и направлений обсуждения.
- [CONTEXT.md](../../CONTEXT.md) — термины, продуктовый смысл, NEXT и LATER.
- [Product v1 contract](../clustering_product_v1_contract.md) — точное текущее поведение режимов и API.
- [Product v1 workflow](../clustering_product_v1_workflow.md) — детали текущего пользовательского и frontend-потока.
- [Open Questions](../project/open-questions.md) — решения, которые ещё не приняты.
