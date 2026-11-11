"""Comparação aritmética de duas hipóteses, sem regras tributárias reais."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[Decimal, Field(ge=0, le=Decimal("1000000000000"), decimal_places=2)]
Rate = Annotated[Decimal, Field(ge=0, le=100, decimal_places=4)]
DISCLAIMER = (
    "Cenário hipotético e educacional. As taxas são informadas pelo usuário; "
    "o cálculo não determina carga tributária real nem constitui orientação tributária. "
    "Não considera créditos, regimes especiais, transição ou incidência por produto."
)


class SimulationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    base_amount: Money = Field(description="Base hipotética em BRL, sem tributo.")
    current_rate_percent: Rate = Field(description="Taxa hipotética atual, em %.")
    proposed_rate_percent: Rate = Field(description="Taxa hipotética proposta, em %.")


class Scenario(BaseModel):
    rate_percent: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class SimulationOutput(BaseModel):
    currency: str = "BRL"
    base_amount: Decimal
    current: Scenario
    proposed: Scenario
    tax_difference: Decimal
    formula: str = "tributo = base_amount × rate_percent / 100; total = base + tributo"
    rounding: str = "Tributo arredondado para centavos com ROUND_HALF_UP."
    disclaimer: str = DISCLAIMER


def simulate(request: SimulationInput) -> SimulationOutput:
    def scenario(rate: Decimal) -> Scenario:
        tax = (request.base_amount * rate / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return Scenario(
            rate_percent=rate, tax_amount=tax, total_amount=request.base_amount + tax
        )

    current = scenario(request.current_rate_percent)
    proposed = scenario(request.proposed_rate_percent)
    return SimulationOutput(
        base_amount=request.base_amount,
        current=current,
        proposed=proposed,
        tax_difference=proposed.tax_amount - current.tax_amount,
    )
