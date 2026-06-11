# Matterhorn Quant — System Architecture

Institutional-grade AI-powered trading platform: end-to-end design, with a
working Python reference implementation in `matterhorn_quant/` that runs the
entire decision pipeline (data → analytics → ML → decision → risk →
execution → monitoring) against historical, synthetic, or live bar data.

---

## 1. Design principles

1. **One pipeline, three modes.** Backtest, paper trading, and live trading
   run the *same code path*; only the data feed and broker adapter change.
   Anything else guarantees that live behavior diverges from what was tested.
2. **Risk has veto power.** Strategies and ML propose; the risk manager
   disposes. No order reaches a broker without passing sizing, exposure,
   VaR, and circuit-breaker checks.
3. **Causality is enforced structurally.** Signals at bar *t* use data
   through *t*; execution happens at *t+1*; models are walk-forward trained.
   Lookahead bias is the most common source of fake alpha.
4. **Costs are first-class.** Slippage (square-root impact), commissions,
   and participation-capped fills are modeled in every backtest. An edge
   that doesn't survive costs is not an edge.
5. **Everything explains itself.** Every signal, decision, and risk action
   carries a human-readable reasoning string and lands in an append-only
   audit log.
6. **Degrade gracefully.** Redundant data providers, heartbeat health
   checks, circuit breakers, and a kill switch ensure failure modes are
   "stop trading," never "trade wrong."

---

## 2. Component architecture

```
                        ┌─────────────────────────────────────────────────┐
                        │                 DATA PLATFORM                   │
  Market data vendors ─▶│  Ingestion adapters (REST/WS/FIX)               │
  (primary + backup)    │  • real-time ticks/bars  • L1/L2 order book     │
  News / filings ──────▶│  • OHLCV history         • trade prints         │
  Social / alt data ───▶│  Validation & failover (FailoverProvider)       │
  Economic calendar ───▶│  Normalization → event bus (Kafka)              │
                        └───────────────┬─────────────────────────────────┘
                                        │ clean, timestamped events
                ┌───────────────────────┼───────────────────────────┐
                ▼                       ▼                           ▼
   ┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐
   │ TECHNICAL ANALYSIS │   │  QUANT MODELS      │   │ SENTIMENT / NLP    │
   │ RSI MACD BB VWAP   │   │ momentum, mean-rev │   │ news, filings,     │
   │ EMA SMA ATR Ichi   │   │ stat-arb/cointegr. │   │ transcripts,       │
   │ Fib, vol profile,  │   │ vol models, factor │   │ social streams →   │
   │ S/R, structure,    │   │ models, Monte Carlo│   │ score + confidence │
   │ liquidity          │   │ regime detection   │   │                    │
   └─────────┬──────────┘   └─────────┬──────────┘   └─────────┬──────────┘
             │                        │                        │
             │              ┌─────────▼──────────┐             │
             │              │  ML PLATFORM       │             │
             │              │ feature store,     │             │
             └─────────────▶│ walk-fwd ensemble, │◀────────────┘
                            │ drift detection,   │
                            │ OOS self-evaluation│
                            └─────────┬──────────┘
                                      │ Signals {strength, confidence, reasoning}
                            ┌─────────▼──────────┐
                            │  DECISION ENGINE   │  adaptive weighted voting,
                            │  (chairs the vote) │  regime tilts, quality
                            └─────────┬──────────┘  filters, ranking
                                      │ TradeDecisions
                            ┌─────────▼──────────┐
                            │   RISK MANAGER     │  vol-target sizing, VaR cap,
                            │   (veto power)     │  exposure limits, stops,
                            └─────────┬──────────┘  circuit breakers, kill switch
                                      │ target portfolio
                  ┌───────────────────┼───────────────────┐
                  ▼                   ▼                   ▼
        ┌──────────────────┐ ┌────────────────┐ ┌──────────────────┐
        │ PORTFOLIO MGMT   │ │ EXECUTION      │ │ MONITORING & OPS │
        │ optimizer,       │ │ validation,    │ │ dashboard, alerts│
        │ rebalancer,      │ │ smart routing, │ │ health, audit,   │
        │ diversification  │ │ broker adapters│ │ reporting        │
        └──────────────────┘ └───────┬────────┘ └──────────────────┘
                                     ▼
                          Brokers / venues (IBKR, Alpaca, FIX)
```

### Multi-agent organization

The platform is structured as cooperating specialist agents (see
`agents/orchestrator.py`), mirroring an institutional desk: a **DataAgent**
(ingestion/quality), one **AnalystAgent per model family**, a
**RegimeAgent**, a **DecisionAgent** chairing the vote, a **RiskAgent** with
veto power, an **ExecutionAgent**, and an **OpsAgent**. Agents exchange
typed messages (`Signal`, `TradeDecision`, `Order`, `Fill`) over a message
bus in production, so each scales and fails independently.

---

## 3. Subsystem detail (and where it lives in this repo)

| Subsystem | Capabilities | Module |
|---|---|---|
| Data platform | provider abstraction, redundancy/failover, data-quality gates, synthetic multi-regime generator | `data/providers.py` |
| Technical analysis | RSI, MACD, Bollinger, VWAP, EMA/SMA, ATR, Ichimoku, Fibonacci, volume profile, support/resistance, trend, breakout, reversal (structure flips), market structure, liquidity (Amihud, dollar volume) | `indicators/` |
| Quant models | time-series momentum, mean reversion, volatility breakout, Engle–Granger cointegration scan + pairs stat-arb, GMM regime detection / market-state classification, Monte Carlo simulation | `strategies/`, `backtest/stress.py` |
| AI/ML | feature engineering (17 stationary features), GBM+RF+logistic ensemble, walk-forward training, drift-triggered refits (online/adaptive learning), OOS-accuracy self-evaluation, feature-importance explainability | `ml/` |
| Sentiment | finance-lexicon scorer with negation/intensifiers, per-symbol aggregation with confidence; FinBERT/LLM scorers slot into the same interface | `sentiment/analyzer.py` |
| Risk | vol-target + fractional-Kelly sizing, per-name/gross/net caps, historical + Cornish–Fisher + Monte Carlo VaR, expected shortfall, ATR dynamic stops/take-profits, daily-loss circuit breaker, drawdown ladder, kill switch | `risk/` |
| Portfolio | shrunk-covariance mean–variance optimizer, risk parity, threshold rebalancing with turnover control | `portfolio/optimizer.py` |
| Decision engine | confidence-weighted voting, online per-strategy weight adaptation, regime tilts, quality filters, opportunity ranking, full reasoning trail | `decision/engine.py` |
| Backtesting | event-driven multi-asset engine, walk-forward analysis, Monte Carlo block bootstrap, crisis scenario analysis; Sharpe/Sortino/MaxDD/win rate/profit factor/risk-reward/CAGR/Calmar | `backtest/` |
| Execution | broker abstraction, pre-trade validation (fat-finger/notional/price bands), TWAP smart routing with latency tracking, square-root impact slippage, partial fills, paper broker | `execution/` |
| Monitoring | structured logging, heartbeat health monitor, severity-routed alert fan-out (email/push/chat channels), append-only JSONL audit log | `monitoring/ops.py` |
| Orchestration | multi-agent cycle coordinator + self-improvement feedback loops | `agents/orchestrator.py` |

### Data sources (production)

* **Prices/volume:** Polygon or Databento (primary), Alpaca/IEX (backup);
  L2 depth from Databento/exchange feeds where the strategy needs it.
* **Fundamentals/earnings:** S&P Capital IQ, FMP, or Polygon fundamentals.
* **Economic/central bank:** FRED, Econoday calendar, central bank RSS.
* **News:** Benzinga/Marketaux/Bloomberg (budget-dependent); EDGAR for
  filings (8-K, 10-Q, Form 4 insider transactions — public and legal);
  13F for institutional holdings (45-day lag — useful for positioning
  context, not timing).
* **Social/alt:** Reddit/X firehose vendors, web-scraped alt data via
  vendors with clean provenance. Alt data must clear legal review
  (material non-public information risk) before ingestion.

---

## 4. Technology stack recommendations

| Layer | Recommendation | Why |
|---|---|---|
| Research & strategy code | **Python 3.11+** (pandas/numpy/scikit-learn/PyTorch) | ecosystem, iteration speed; this is where edge is found |
| Hot path (live execution, market data handlers) | **Rust** (or Go) services | predictable latency, no GC pauses; only needed below ~10ms ambitions |
| Event bus | **Kafka** (or Redpanda) | replayable event log = backtest/live parity and disaster recovery |
| Time-series store | **TimescaleDB** (PostgreSQL) or **ClickHouse** | bars/ticks at scale, SQL access for research |
| Reference data, orders, audit | **PostgreSQL** | transactional integrity for the records that matter legally |
| Hot cache / feature store | **Redis** | sub-ms feature reads on the live path |
| Object store | **S3** (+ Parquet) | raw vendor payloads, model artifacts, backups |
| ML lifecycle | **MLflow** registry + experiment tracking | model versioning, promotion gates |
| Dashboard / API | **FastAPI** + **Grafana** (metrics) + a React panel | real-time book/risk view |
| Alerting | Prometheus → Alertmanager → PagerDuty/SNS (email + mobile push) | severity routing, on-call escalation |
| Secrets | AWS Secrets Manager / Vault; KMS-encrypted at rest | never in code or env files |
| Orchestration | Kubernetes (EKS) or ECS; Airflow/Dagster for batch jobs | isolation per agent/service |

### Cloud / deployment architecture

```
AWS (us-east-1, two AZs)
├─ VPC (private subnets; egress only to vendors/brokers via NAT)
│  ├─ EKS cluster
│  │   ├─ data-ingest (per vendor; autoscaled)        [stateless]
│  │   ├─ analytics & ml-inference services           [stateless]
│  │   ├─ decision-engine + risk-manager (active/standby pair)
│  │   ├─ execution-gateway (broker adapters; pinned, low-latency node)
│  │   └─ ops: dashboard, alerting, report generator
│  ├─ MSK (Kafka), ElastiCache (Redis)
│  ├─ RDS PostgreSQL/Timescale (multi-AZ, PITR backups)
│  └─ S3 (raw data, models, WORM audit archive) + Glacier DR copies
├─ Batch/research: Airflow on spot instances; GPU nodes on demand
└─ Failover: standby region with replicated S3/RDS snapshots;
   RTO target < 1h for research, < 5 min for "flatten and halt"
```

**Disaster recovery posture:** the safe state is *flat and halted*. The
execution gateway keeps broker-side kill ability (cancel-all + liquidate)
even if the decision tier is down; a dead-man's heartbeat at the broker
adapter flattens the book if the risk service stops responding.

### Security

* API keys/credentials in a secrets manager, KMS-encrypted, rotated; IAM
  roles per service (least privilege); no secrets in code/CI logs.
* mTLS between services; private subnets; broker/vendor IP allowlists.
* RBAC for humans (read-only research vs. trade-enabled ops); hardware MFA.
* Append-only audit trail (orders, fills, decisions, risk overrides,
  config changes) to WORM storage — also a regulatory requirement.
* Automated daily backups + restore drills; infrastructure as code so the
  whole stack is rebuildable.

---

## 5. Data flow (one decision cycle)

```
vendor feeds ──▶ ingest ──▶ validate/normalize ──▶ event bus
                                                     │
              ┌──────────────┬───────────────┬───────┘
              ▼              ▼               ▼
        indicator calc   feature store   sentiment scoring
              │              │               │
              ▼              ▼               ▼
        strategy signals  ML inference   sentiment signals
              └──────────────┼───────────────┘
                             ▼
                  decision engine (votes, filters, ranks)
                             ▼
                  risk manager (sizes, caps, or vetoes)
                             ▼
                  portfolio targets → rebalance deltas
                             ▼
                  execution gateway (validate → route → fill)
                             ▼
              fills ──▶ positions/PnL ──▶ monitoring + audit
                             │
                             └──▶ outcome tracking ──▶ adaptive weights,
                                  ML OOS evaluation, drift checks  (feedback)
```

The feedback edge at the bottom is the **self-improvement loop**, and it is
implemented, not aspirational: realized outcomes update per-strategy voting
weights online, gate ML confidence by out-of-sample accuracy, trigger
drift-based refits, and scale risk by regime and drawdown.

---

## 6. Development roadmap (MVP → production)

**Phase 0 — Foundations (weeks 1–4).** Repo, CI, data layer with two
providers + failover, TimescaleDB schema, the typed core (this repo's
`core/types.py`), logging/audit skeleton. *Exit: clean daily bars for 500
symbols, replayable.*

**Phase 1 — Research MVP (weeks 5–10).** Indicator engine, 2–3 classic
strategies, cost-aware backtester with full metrics, walk-forward harness.
*Exit: a backtest you trust — verified causality, costs, and a null result
on shuffled data.*

**Phase 2 — Decision & risk core (weeks 11–16).** Decision engine, risk
manager (sizing → VaR → breakers → kill switch), portfolio optimizer,
stress/Monte Carlo. *Exit: risk report per backtest; chaos tests prove the
kill switch fires.*

**Phase 3 — ML & sentiment (weeks 17–24).** Feature store, walk-forward
ensemble, drift detection, sentiment ingestion + scoring, regime detector.
*Exit: ML adds OOS value vs. Phase 1 baseline or it doesn't ship.*

**Phase 4 — Paper trading (weeks 25–32).** Broker abstraction + paper
adapter, smart routing, dashboard, alerting, health checks. Run the full
loop daily for ≥ 2 months. *Exit: paper results within tolerance of
backtest expectations (slippage, fill rates, turnover).*

**Phase 5 — Limited live (weeks 33–40).** Smallest viable capital, one
broker, conservative limits (half-size everything). Reconcile every fill.
*Exit: 3 months live, tracking paper within tolerance, zero risk-limit
breaches unexplained.*

**Phase 6 — Production hardening (weeks 41–52).** Multi-AZ failover, DR
drills, capacity scaling, model registry promotion gates, compliance
review, automated reporting. Scale capital stepwise only as live evidence
accumulates.

---

## 7. Scalability considerations

* **Universe:** the daily-bar pipeline scales linearly; 5,000 symbols is a
  config change (the cointegration scan is O(n²) — pre-filter by sector
  and correlation, as implemented).
* **Frequency:** daily/weekly → intraday requires the Rust hot path, L2
  feeds, colocation decisions, and a different cost model. Do not attempt
  HFT — that is a different business with a different cost structure.
* **Capacity:** strategy capacity is bounded by liquidity (`liquidity_profile`
  feeds this): square-root impact means doubling AUM more than doubles
  impact cost on the same signals. Mid-frequency equity strategies of this
  type typically degrade noticeably past low hundreds of $M.
* **Compute:** model training is embarrassingly parallel (per-fold,
  per-family); inference is batched (as in `WalkForwardEnsemble`).
* **Organizational:** the agent/message-bus decomposition lets teams own
  subsystems independently — the real scaling constraint.

---

## 8. Weaknesses and limitations (read this before believing any backtest)

1. **Alpha decay.** Public-knowledge signals (momentum, mean reversion,
   simple ML on price features) are heavily arbitraged. Expect realized
   edge far below historical backtests, and expect it to decay.
2. **Overfitting risk is structural.** Thousands of researcher decisions
   (features, thresholds, windows) silently fit the past. Walk-forward
   testing reduces but does not eliminate this; only out-of-sample *time*
   (paper/live) is conclusive evidence.
3. **Regime breaks.** Models trained on history fail when the data-generating
   process changes (2008, 2020, rate shocks). The regime detector reacts
   with a lag, never in advance.
4. **Cost-model error compounds.** Real slippage in stress is worse than
   any model; liquidity vanishes exactly when you need it.
5. **Sentiment/alt-data fragility.** Vendor coverage changes, social data
   is gameable (pump campaigns), and NLP misreads sarcasm and context.
6. **Single-operator risk.** Institutional desks have independent risk
   officers. An automated risk layer enforces discipline only if humans
   don't override it under pressure.
7. **This reference implementation** uses daily bars, simulated L1 fills,
   and synthetic data for the demo; production requires real vendor
   integration, corporate-action handling, survivorship-bias-free
   universes, and regulatory/compliance work not represented here.

## 9. Failure scenarios and mitigations

| Scenario | Impact | Mitigation (implemented / planned) |
|---|---|---|
| Data vendor outage / bad ticks | wrong signals | failover chain + validation gates (impossible prices, NaNs, >50% jumps) |
| Flash crash | stops blown through, fills far from marks | participation caps, price-band order validation, circuit breaker, kill switch |
| Model drift / silent alpha decay | slow bleed | OOS-accuracy gating, drift-triggered refits, adaptive strategy weights fade losers |
| Correlated crowded-trade unwind | "market-neutral" book loses on both legs | gross-exposure cap, VaR cap, scenario analysis with vol-drag term |
| Broker API failure mid-rebalance | unknown position state | reconciliation on every cycle; halt on mismatch; dead-man flatten |
| Risk service crash | uncontrolled book | broker-side dead-man heartbeat → cancel-all + flatten |
| Fat-finger / bad config | absurd order | pre-trade validation (notional %, price deviation), audit of config changes |
| Drawdown spiral | capital destruction | drawdown ladder de-risks progressively; hard stop liquidates and halts for human review |
| Compromised credentials | theft / rogue orders | secrets manager, rotation, IP allowlists, withdrawal-disabled API keys, RBAC |
| Exchange halt / circuit breaker day | can't exit | position caps sized so overnight gap risk ≤ daily loss budget; index hedge playbook |

---

## 10. What "institutional-grade" ultimately means here

Not the model zoo — the discipline: enforced causality, costs in every
number, risk with veto power, audit of every action, graceful failure, and
the humility to size by evidence. The performance expectations that follow
from this discipline are quantified in [PERFORMANCE.md](PERFORMANCE.md).
