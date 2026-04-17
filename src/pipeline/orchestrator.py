"""
Pipeline Orchestrator — Tourism Monitor Cozumel
Secuenciador determinista de fases del pipeline de datos.
Inspirado en el patrón ADW (Agentic Developer Workflows).
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

STATE_FILE = Path("data/pipeline_state.json")


# ─── TIPOS ─────────────────────────────────────────────────────────────

class WorkflowType(str, Enum):
    DAILY_UPDATE = "daily_update"
    WEEKLY_UPDATE = "weekly_update"
    HISTORICAL_BACKFILL = "historical_backfill"
    SHIPS_MASTER_REFRESH = "ships_master_refresh"


class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineState:
    last_daily_update: Optional[str] = None        # ISO timestamp
    last_weekly_update: Optional[str] = None       # ISO timestamp
    last_historical_date: Optional[str] = None     # date string YYYY-MM-DD
    total_records: int = 0
    last_run_errors: list = field(default_factory=list)
    last_run_workflow: Optional[str] = None
    last_run_timestamp: Optional[str] = None

    @classmethod
    def load(cls) -> "PipelineState":
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return cls(**data)
        return cls()

    def save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2))


@dataclass
class PhaseResult:
    phase: str
    status: PhaseStatus
    records_processed: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_quarantined: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


# ─── ORQUESTADOR ────────────────────────────────────────────────────────

class PipelineOrchestrator:
    """
    Orquestador del pipeline de datos.
    Ejecuta fases en secuencia, persiste estado y maneja errores.
    """

    WORKFLOW_PHASES = {
        WorkflowType.DAILY_UPDATE: [
            "collect_programacion",
            "validate",
            "process",
            "store",
            "notify",
        ],
        WorkflowType.WEEKLY_UPDATE: [
            "collect_historico",
            "validate",
            "process",
            "enrich",
            "store",
            "notify",
        ],
        WorkflowType.HISTORICAL_BACKFILL: [
            "collect_historico_range",
            "validate",
            "process",
            "enrich",
            "store",
            "notify",
        ],
        WorkflowType.SHIPS_MASTER_REFRESH: [
            "collect_ships",
            "validate_ships",
            "store_ships",
            "notify",
        ],
    }

    def __init__(self):
        self.state = PipelineState.load()

    def run(
        self,
        workflow: WorkflowType,
        dry_run: bool = False,
        **kwargs,
    ) -> list[PhaseResult]:
        """
        Ejecuta un workflow completo.

        Args:
            workflow: tipo de workflow a ejecutar
            dry_run: si True, no persiste nada en Supabase
            **kwargs: argumentos adicionales para fases (ej. date_from, date_to)

        Returns:
            Lista de PhaseResult por cada fase ejecutada
        """
        phases = self.WORKFLOW_PHASES[workflow]
        results = []

        logger.info(f"\n{'='*50}")
        logger.info(f"🚀 Pipeline: {workflow.value}")
        logger.info(f"   Fases: {' → '.join(phases)}")
        logger.info(f"   Dry run: {dry_run}")
        logger.info(f"{'='*50}")

        start_time = datetime.now()

        for phase_name in phases:
            logger.info(f"\n▶ Fase: {phase_name}")
            phase_start = datetime.now()

            try:
                result = self._run_phase(phase_name, workflow, dry_run, **kwargs)
                result.duration_seconds = (datetime.now() - phase_start).total_seconds()
                results.append(result)

                if result.status == PhaseStatus.FAILED:
                    logger.error(f"❌ Fase '{phase_name}' falló: {result.error}")
                    logger.error("   Pipeline abortado.")
                    break

                logger.info(
                    f"✅ {phase_name} completado "
                    f"({result.records_new} nuevos, "
                    f"{result.records_updated} actualizados) "
                    f"en {result.duration_seconds:.1f}s"
                )

            except Exception as e:
                result = PhaseResult(
                    phase=phase_name,
                    status=PhaseStatus.FAILED,
                    error=str(e),
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                )
                results.append(result)
                logger.exception(f"❌ Excepción en fase '{phase_name}'")
                break

        # Actualizar estado
        total_duration = (datetime.now() - start_time).total_seconds()
        errors = [r.error for r in results if r.error]

        self.state.last_run_workflow = workflow.value
        self.state.last_run_timestamp = datetime.now().isoformat()
        self.state.last_run_errors = errors

        if workflow == WorkflowType.DAILY_UPDATE:
            self.state.last_daily_update = datetime.now().isoformat()
        elif workflow == WorkflowType.WEEKLY_UPDATE:
            self.state.last_weekly_update = datetime.now().isoformat()

        if not dry_run:
            self.state.save()

        # Resumen final
        total_new = sum(r.records_new for r in results)
        total_updated = sum(r.records_updated for r in results)
        total_quarantined = sum(r.records_quarantined for r in results)
        success = all(r.status != PhaseStatus.FAILED for r in results)

        logger.info(f"\n{'='*50}")
        logger.info(f"{'✅ Pipeline completado' if success else '❌ Pipeline con errores'}")
        logger.info(f"   Nuevos: {total_new} | Actualizados: {total_updated} | Quarantine: {total_quarantined}")
        logger.info(f"   Duración total: {total_duration:.1f}s")
        logger.info(f"{'='*50}\n")

        return results

    def _run_phase(
        self,
        phase_name: str,
        workflow: WorkflowType,
        dry_run: bool,
        **kwargs,
    ) -> PhaseResult:
        """Despacha cada fase al método correspondiente."""
        # Import lazy para evitar dependencias circulares
        phase_methods = {
            "collect_programacion": self._phase_collect_programacion,
            "collect_historico": self._phase_collect_historico,
            "collect_historico_range": self._phase_collect_historico_range,
            "collect_ships": self._phase_collect_ships,
            "validate": self._phase_validate,
            "validate_ships": self._phase_validate,
            "process": self._phase_process,
            "enrich": self._phase_enrich,
            "store": self._phase_store,
            "store_ships": self._phase_store,
            "notify": self._phase_notify,
        }

        method = phase_methods.get(phase_name)
        if not method:
            raise ValueError(f"Fase desconocida: {phase_name}")

        return method(dry_run=dry_run, **kwargs)

    # ── STUBS DE FASES ─────────────────────────────────────────────────
    # Implementación real en cada módulo src/collectors/, src/processors/

    def _phase_collect_programacion(self, dry_run=False, **kwargs) -> PhaseResult:
        from src.collectors.apiqroo import scrape_programacion
        df = scrape_programacion()
        self._context = {"df_raw": df}
        return PhaseResult("collect_programacion", PhaseStatus.SUCCESS, records_processed=len(df))

    def _phase_collect_historico(self, dry_run=False, **kwargs) -> PhaseResult:
        target_date = kwargs.get("target_date", date.today() - timedelta(days=7))
        from src.collectors.apiqroo import scrape_historico_month
        df = scrape_historico_month(target_date.year, target_date.month)
        self._context = {"df_raw": df}
        return PhaseResult("collect_historico", PhaseStatus.SUCCESS, records_processed=len(df))

    def _phase_collect_historico_range(self, dry_run=False, **kwargs) -> PhaseResult:
        date_from = kwargs.get("date_from", date(2015, 10, 1))
        date_to = kwargs.get("date_to", date.today())
        from src.collectors.apiqroo import scrape_historico_range
        df = scrape_historico_range(date_from, date_to)
        self._context = {"df_raw": df}
        return PhaseResult("collect_historico_range", PhaseStatus.SUCCESS, records_processed=len(df))

    def _phase_collect_ships(self, dry_run=False, **kwargs) -> PhaseResult:
        from src.collectors.cruisemapper import scrape_ships_master
        df = scrape_ships_master()
        self._context = {"df_ships": df}
        return PhaseResult("collect_ships", PhaseStatus.SUCCESS, records_processed=len(df))

    def _phase_validate(self, dry_run=False, **kwargs) -> PhaseResult:
        from .hooks.pre_store_validation import validate
        df = self._context.get("df_raw") or self._context.get("df_ships")
        validate(df, stage="validate")
        return PhaseResult("validate", PhaseStatus.SUCCESS, records_processed=len(df))

    def _phase_process(self, dry_run=False, **kwargs) -> PhaseResult:
        from src.processors.cleaner import clean
        df_clean = clean(self._context["df_raw"])
        self._context["df_clean"] = df_clean
        return PhaseResult("process", PhaseStatus.SUCCESS, records_processed=len(df_clean))

    def _phase_enrich(self, dry_run=False, **kwargs) -> PhaseResult:
        from src.processors.enricher import enrich
        df_enriched = enrich(self._context["df_clean"])
        self._context["df_enriched"] = df_enriched
        return PhaseResult("enrich", PhaseStatus.SUCCESS, records_processed=len(df_enriched))

    def _phase_store(self, dry_run=False, **kwargs) -> PhaseResult:
        if dry_run:
            logger.info("   [DRY RUN] Skip store")
            return PhaseResult("store", PhaseStatus.SKIPPED)
        from src.db.client import upsert_cruise_visits
        df = self._context.get("df_enriched") or self._context.get("df_clean") or self._context.get("df_ships")
        new, updated = upsert_cruise_visits(df)
        self.state.total_records += new
        return PhaseResult("store", PhaseStatus.SUCCESS, records_new=new, records_updated=updated)

    def _phase_notify(self, dry_run=False, **kwargs) -> PhaseResult:
        logger.info("   Pipeline completado — estado guardado en data/pipeline_state.json")
        return PhaseResult("notify", PhaseStatus.SUCCESS)
