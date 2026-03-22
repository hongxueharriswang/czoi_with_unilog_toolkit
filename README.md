

# CZOI Toolkit

> **Constrained Zoned‑Object Infrastructure (CZOI)** — a modular Python toolkit for building, simulating, and maintaining **secure and intelligent integrated organizational systems** with zones, roles, permissions, formal constraints (UniLang), neural components, semantic embeddings, daemons, and a simulation engine. 

This version of the CZOI toolkit incorporates UniLog for constraint representation and reasoning, enabling more precise and expressive modeling and resolution of diverse constraints. This approach improves upon earlier versions of CZOI, which relied on native Python expressions for constraint specification and handling.

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Alpha%200.1.0-orange.svg)](#roadmap)
[![Tests](https://img.shields.io/badge/tests-coming%20soon-lightgrey.svg)](#contributing)
***

## Table of Contents

*   why-czoi
*   features
*   installation
*   quickstart
*   core-concepts
*   architecture
*   cli
*   integrations
*   storage--persistence
*   neural--embeddings
*   simulation--daemons
*   examples
*   roadmap
*   contributing
*   license
*   citing-czoi

***

## Why CZOI?

CZOI is a concrete Python implementation of the **Constrained Zoned‑Object Architecture (CZOA)**, which unifies concepts from Constrained Object Hierarchies (COH) with practical **zoned role‑based (ZRB) system design, implementation, maintenance and access control**, constraints, logic, and learning. It models an intelligent integrated organizational system as a 10‑tuple  
$$\mathcal{S} = (Z, R, U, A, O, N, E, \Gamma, \Phi, \Delta)$$ — zones, roles, users, apps/operations, neural components, embeddings, constraints (Gamma), permission calculus (Phi), and daemons. This gives you a single end‑to‑end framework to **design, verify, operate, and evolve** real organizational systems. 

CZOI specializes the more general **GISMOL** toolkit (for COH), adding zones, roles, permissions, and gamma mappings while **reusing a common logic foundation (UniLog/UniLang)**. 

***

## Features

*   **Core modeling**: Zones, Roles, Users, Applications, Operations, GammaMappings, and a `System` container. 
*   **Permission engine**: Compute effective permissions (base + inheritance + gamma) and decide access with contextual constraints. 
*   **Constraints (Gamma)**: Identity, Trigger, Goal, and Access constraints expressed in Python or **UniLang** logic, with safe evaluation and a formal inference engine. 
*   **UniLang logic**: Parser, AST, and pluggable solvers (classical, modal, temporal, fuzzy, etc.). 
*   **Neural components**: Anomaly detection, role mining; easy to add custom ML modules. 
*   **Semantic embeddings**: Vector stores, in‑memory implementation, and an `EmbeddingService`. 
*   **Daemons**: Long‑running monitors (security, compliance) and **UniLang‑triggered** actions. 
*   **Simulation engine**: Drive time‑based scenarios, generate logs, and analyze outcomes. 
*   **Web integrations**: Django, Flask, FastAPI decorators/middleware for permission checks. 
*   **CLI**: Initialize systems, check permissions, simulate, audit, migrate, train, and run daemons. 

***

## Installation

### Core

```bash
pip install czoi
```

Installs the core toolkit and essential dependencies (`numpy`, `networkx`, `sqlalchemy`, …). 

### Extras

```bash
# Neural components (PyTorch / scikit-learn / transformers)
pip install czoi[neural]

# REST API (FastAPI + uvicorn)
pip install czoi[api]

# Web frameworks
pip install czoi[django]
pip install czoi[flask]

# Everything
pip install czoi[all]
```

These extras enable neural, API, and framework integrations out of the box. 

### Development

```bash
git clone https://github.com/hongxueharriswang/czoi_toolkit.git
cd czoi
pip install -e .[dev]
```

Editable install for local development and contributions. 

***

## Quickstart

### 1) Define a minimal system

```python
from czoi.core import System, Zone, Role, User, Application

system = System()
root = Zone("Root")
hr = Zone("HR", parent=root)
system.add_zone(hr)

manager = Role("Manager", hr)
assistant = Role("Assistant", hr)
system.add_role(manager)
system.add_role(assistant)

app = Application("HR App")
view_op = app.add_operation("view_employee", "GET")
edit_op = app.add_operation("edit_employee", "POST")
system.add_application(app)

manager.grant_permission(view_op)
manager.grant_permission(edit_op)
assistant.grant_permission(view_op)

alice = User("alice")
alice.assign_role(hr, assistant)
system.add_user(alice)
```

A basic HR zone with roles and operations. 

### 2) Add constraints (Python or UniLang)

```python
from czoi.constraint import Constraint, ConstraintType

c1 = Constraint(
    "NoSelfReview",
    ConstraintType.ACCESS,
    {"roles": ["Manager"]},
    "user != employee"
)
# UniLang example
c2 = Constraint(
    "ZoneContainment",
    ConstraintType.IDENTITY,
    {"zones": "all"},
    "G (forall u (inZone(u,z) -> inZone(u,parent(z))))"
)
```

CZOI evaluates Python expressions safely and routes UniLang formulas to the inference engine. 

### 3) Decide permissions

```python
from czoi.permission import SimpleEngine
engine = SimpleEngine(system)
allowed = engine.decide(alice, view_op, hr, {})
print(allowed)  # True
```

The engine computes effective permissions and applies access constraints. 

***

## Core Concepts

*   **Zones (`Zone`)**: Organizational units in a tree; hold roles, users, and apps. 
*   **Roles (`Role`)**: Job functions with base permissions and role hierarchies. 
*   **Users (`User`)**: Assigned to roles within zones (optionally weighted). 
*   **Applications / Operations**: Executable operations grouped by app. 
*   **Gamma mappings (`GammaMapping`)**: Inter‑zone role inheritance with weights/priorities. 
*   **Constraints (`Constraint`)**: Identity, Trigger, Goal, Access; defined in Python/UniLang and managed by `ConstraintManager`. 
*   **Permission engine**: Computes effective permissions and `decide(...)`. 
*   **UniLang**: Unified logic language (classical FOL, modal, temporal, probabilistic, fuzzy, description logics). 

***

## Architecture

```text
czoi/
├── __init__.py
├── core.py           # Zone, Role, User, Application, Operation, GammaMapping, System
├── permission.py     # PermissionEngine, SimpleEngine
├── constraint.py     # Constraint, ConstraintType, ConstraintManager
├── neural.py         # NeuralComponent, AnomalyDetector, RoleMiner
├── embedding.py      # VectorStore, InMemoryVectorStore, EmbeddingService
├── daemon.py         # Daemon, SecurityDaemon, ComplianceDaemon, TriggeredDaemon
├── simulation.py     # SimulationEngine
├── storage.py        # Storage (SQLAlchemy)
├── utils.py          # safe_eval, logging helpers
├── integrations/     # django.py, flask.py, fastapi.py
├── cli.py            # Command-line interface
└── unilog/           # UniLang parser & inference engine
```

Modular layout with clear extension points for solvers, neural components, daemons, and storage adapters. 

### Data Flow (high‑level)

*   Define a system with `core` classes and persist via `Storage`.
*   The `PermissionEngine` consults roles, gamma mappings, and constraints to decide access.
*   Constraints are evaluated through `safe_eval` or **UniLang**’s inference engine.
*   Neural components learn from logs; embeddings support similarity and search.
*   Daemons monitor state and trigger actions; simulations drive time and log events. 

***

## CLI

```bash
czoi init --config system.yaml            # initialize from YAML
czoi check --user alice --op view_patient --zone hosp
czoi simulate --duration 1h --output sim.json
czoi audit --since 2026-03-01
czoi migrate add-zone --name "NewClinic" --parent "North"
czoi train --model anomaly --data logs.csv --output model.pkl
czoi daemon start security --threshold 0.9
```

Use the CLI for administration, verification, simulation, auditing, migrations, training, and daemon control. 

***

## Integrations

### Django

```python
# settings.py
MIDDLEWARE = ['czoi.integrations.django.middleware.CZOAMiddleware']

# views.py
from czoi.integrations.django.decorators import require_permission

@require_permission('view_patient', mode='i_rzbac')
def patient_detail(request, id):
    ...
```

### FastAPI

```python
from fastapi import Depends
from czoi.integrations.fastapi import require_permission

@app.get("/secure")
def endpoint(_ = Depends(require_permission("read:secure"))):
    ...
```

Decorators and middleware apply permission checks consistently across web stacks. (Flask decorators also included.) 

***

## Storage & Persistence

The SQLAlchemy layer persists zones, roles, users, operations, assignments, gamma mappings, constraints, daemons, and audit logs. Vector stores (e.g., `pgvector`) can be integrated via adapters. 

```python
from czoi.storage import Storage

storage = Storage("sqlite:///system.db")
storage.save_system(system)
loaded_system = storage.load_system()
```

 

***

## Neural & Embeddings

*   **Neural components**:
    *   `AnomalyDetector` (IsolationForest)
    *   `RoleMiner` (HDBSCAN clustering)  
        Extend by subclassing `NeuralComponent` and implementing `train`, `predict`, `save`, `load`. 

*   **Embeddings**:  
    `EmbeddingService` with `VectorStore` abstraction and an `InMemoryVectorStore` implementation. 

```python
from czoi.neural import AnomalyDetector
from czoi.embedding import EmbeddingService, InMemoryVectorStore

detector = AnomalyDetector()
# ... train/persist detector

store = InMemoryVectorStore()
svc = EmbeddingService(store, embedder=detector)
# svc.embed_entity(...); svc.update_embedding(...); svc.find_similar(...)
```

 

***

## Simulation & Daemons

*   **SimulationEngine**: subclass and implement `step(current_time)` to generate events; use `run(duration, step)` to execute and `analyze()` / `save_logs()` for results. 

*   **Daemons**:
    *   `SecurityDaemon` (access anomaly monitoring & blocking)
    *   `ComplianceDaemon` (regulatory checks)
    *   `TriggeredDaemon` (execute action when a UniLang formula becomes true) 

```python
from czoi.daemon import TriggeredDaemon

daemon = TriggeredDaemon(
    name="alert_on_accident",
    formula="G (accident(L) -> F_[0,2] vms_message(L,'Accident'))",
    interval=1.0
)
daemon.register_callback(lambda ctx: print("Violation:", ctx))
```

 

***

## Examples

See `examples/` for two case studies:

*   **Healthcare**: Regions → Hospitals → Departments; SoD constraints (prescribe/dispense), temporal alerts, sepsis risk predictor.
*   **Financial trading**: Desks (Equities, Fixed Income); roles for Trader, RiskManager, ComplianceOfficer; position limits and insider‑trading constraints; manipulation detection. 

***

## Roadmap

Planned directions include: additional UniLang solvers (temporal model checking), more vector‑store backends, expanded web adapters, and richer simulation analytics. Contributions are welcome—see below. 

***

## Contributing

1.  **Fork** the repo and create a feature branch.
2.  **Install dev deps**: `pip install -e .[dev]`
3.  **Run tests** and add docs/examples where relevant.
4.  Open a **pull request** with a clear description and rationale. 

***

## License

This project’s license is defined in `LICENSE` at the repository root. (If not present yet, choose one—e.g., MIT or Apache‑2.0—and update this section accordingly.) *(Administrative note for maintainers.)*  
*Repository:* <https://github.com/hongxueharriswang/czoi_toolkit> 

***

## Citing CZOI

If you use CZOI in academic work, please cite:

*   H. Wang, **“Constrained Zone‑Object Architecture (CZOA): A Unified Formalism Integrating Hierarchical Intelligence and Zoned Organizational Intelligent Information Systems,”** 2026. 
*   H. Wang, **“UniLog: A Unified Logic Framework for Constraint Specification in Intelligent Systems,”** *Journal of Applied Logics*, 2026. 
*   H. Wang, **“The Soundness and Completeness of the UniLog Framework,”** *Journal of Logical and Algebraic Methods in Programming*, 2026. 

For API docs, see **<https://czoi.readthedocs.io>** (work in progress). 

***

### Maintainers & Contact

*   **Author**: Harris Wang (Athabasca University, Canada) — <harrisw@athabascau.ca> 

***

### Appendix: API (Quick Index)

Key classes/functions with modules:

*   `core`: `Zone`, `Role`, `User`, `Application`, `Operation`, `GammaMapping`, `System`
*   `permission`: `PermissionEngine`, `SimpleEngine`
*   `constraint`: `Constraint`, `ConstraintManager`, `ConstraintType`
*   `unilog`: `UniLangParser`, `InferenceEngine`
*   `neural`: `NeuralComponent`, `AnomalyDetector`, `RoleMiner`
*   `embedding`: `VectorStore`, `InMemoryVectorStore`, `EmbeddingService`
*   `daemon`: `Daemon`, `TriggeredDaemon`, `SecurityDaemon`, `ComplianceDaemon`
*   `simulation`: `SimulationEngine`
*   `storage`: `Storage`
*   `utils`: `safe_eval`
*   `integrations`: Django / Flask / FastAPI adapters
*   `cli`: `czoi` entry point 

***
