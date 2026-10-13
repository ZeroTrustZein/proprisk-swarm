"""Domain models and calculation schemas for CRE debt sizing and DCF valuation."""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

from proprisk_swarm.types.base import BaseEntity


class LoanType(str, Enum):
    """Mortgage debt financing product types."""

    FIXED_RATE = "fixed_rate"
    FLOATING_SOFR = "floating_sofr"
    MEZZANINE = "mezzanine"
    BRIDGE = "bridge"
    AGENCY = "agency"


class FinancingAssumptions(BaseModel):
    """Mortgage debt financing covenants and terms."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    loan_amount: float = Field(..., ge=0.0, description="Principal initial loan balance")
    loan_type: LoanType = Field(default=LoanType.FIXED_RATE, description="Debt structure")
    interest_rate: float = Field(
        ..., ge=0.0, le=0.40, description="Annual coupon / nominal interest rate"
    )
    term_years: int = Field(default=10, ge=1, le=40, description="Maturity term in years")
    amortization_years: int = Field(
        default=30, ge=1, le=40, description="Amortization basis in years"
    )
    interest_only_years: int = Field(default=0, ge=0, description="Interest-only period in years")
    origination_fee_pct: float = Field(
        default=0.01, ge=0.0, le=0.10, description="Lender origination fee %"
    )
    exit_fee_pct: float = Field(default=0.0, ge=0.0, le=0.05, description="Payoff or exit fee %")
    min_dscr_covenant: float = Field(
        default=1.25, ge=1.0, description="Minimum DSCR required by lender"
    )
    max_ltv_covenant: float = Field(
        default=0.75, ge=0.10, le=1.0, description="Maximum LTV allowed by lender"
    )

    @model_validator(mode="after")
    def validate_term_structure(self) -> FinancingAssumptions:
        """Verify interest-only period does not exceed loan maturity term."""
        if self.interest_only_years > self.term_years:
            raise ValueError(
                f"interest_only_years ({self.interest_only_years}) cannot exceed term_years ({self.term_years})"
            )
        if self.term_years > self.amortization_years:
            raise ValueError(
                f"term_years ({self.term_years}) cannot exceed amortization_years ({self.amortization_years})"
            )
        return self

    @property
    def monthly_interest_rate(self) -> float:
        """Monthly decimal rate."""
        return self.interest_rate / 12.0

    @property
    def origination_fee_amount(self) -> float:
        """Dollar cost of loan origination."""
        return self.loan_amount * self.origination_fee_pct

    def monthly_amortizing_payment(self) -> float:
        """Standard monthly principal and interest payment based on amortization schedule."""
        if self.loan_amount <= 0.0:
            return 0.0
        n_months = self.amortization_years * 12
        r = self.monthly_interest_rate
        if r == 0.0:
            return self.loan_amount / n_months
        payment = self.loan_amount * (r * (1 + r) ** n_months) / ((1 + r) ** n_months - 1)
        return payment

    def annual_debt_service(self, year_index: int) -> float:
        """Annual scheduled debt service based on interest-only status."""
        if self.loan_amount <= 0.0:
            return 0.0
        if year_index <= self.interest_only_years:
            return self.loan_amount * self.interest_rate
        return self.monthly_amortizing_payment() * 12.0


class LoanAmortizationRow(BaseModel):
    """Periodic record of principal and interest allocation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    month: int = Field(..., ge=1, description="Sequential month number")
    beginning_balance: float = Field(..., ge=0.0, description="Balance at month start")
    payment: float = Field(..., ge=0.0, description="Total monthly payment")
    principal: float = Field(..., ge=0.0, description="Portion applied to principal")
    interest: float = Field(..., ge=0.0, description="Portion applied to interest")
    ending_balance: float = Field(..., ge=0.0, description="Balance at month end")


class DCFParameters(BaseModel):
    """Underwriting macroeconomic and property growth assumptions for DCF modeling."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    holding_period_years: int = Field(
        default=5, ge=1, le=20, description="Investment horizon in years"
    )
    exit_cap_rate: float = Field(
        ..., ge=0.01, le=0.25, description="Terminal exit capitalization rate"
    )
    discount_rate: float = Field(
        default=0.09, ge=0.01, le=0.30, description="Discount rate / target hurdle rate"
    )
    annual_rent_growth: float = Field(
        default=0.03, ge=-0.10, le=0.20, description="Annual nominal rent escalation"
    )
    annual_opex_growth: float = Field(
        default=0.025, ge=-0.05, le=0.20, description="Annual expense inflation"
    )
    general_inflation_rate: float = Field(
        default=0.025, ge=-0.05, le=0.20, description="General CPI inflation"
    )
    disposition_cost_pct: float = Field(
        default=0.015, ge=0.0, le=0.10, description="Brokerage and legal closing cost at sale"
    )


class AnnualCashFlow(BaseModel):
    """Detailed pro-forma annual cash flow line items."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    year: int = Field(..., ge=1, description="Pro-forma timeline year index")
    potential_gross_revenue: float = Field(..., ge=0.0, description="Gross potential income")
    vacancy_and_credit_loss: float = Field(default=0.0, ge=0.0, description="Economic vacancy loss")
    effective_gross_income: float = Field(
        ..., ge=0.0, description="Net operational revenue collected"
    )
    operating_expenses: float = Field(..., ge=0.0, description="Operational expenditures")
    net_operating_income: float = Field(..., description="Net Operating Income before debt service")
    capex_reserves: float = Field(
        default=0.0, ge=0.0, description="Capital expenditures and replacement reserve"
    )
    debt_service: float = Field(
        default=0.0, ge=0.0, description="Annual principal and interest payment"
    )
    unlevered_cash_flow: float = Field(
        ..., description="Cash flow before debt service (NOI - Capex)"
    )
    levered_cash_flow: float = Field(
        ..., description="Cash flow after debt service to equity investors"
    )
    ending_loan_balance: float = Field(
        default=0.0, ge=0.0, description="Remaining principal debt at year end"
    )
    dscr: float = Field(
        default=0.0, ge=0.0, description="Debt Service Coverage Ratio (NOI / Debt Service)"
    )
    debt_yield: float = Field(
        default=0.0, ge=0.0, description="Debt Yield (NOI / Ending Loan Balance)"
    )


class ValuationMetrics(BaseModel):
    """Summary return and risk metrics produced by DCF model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    purchase_price: float = Field(..., gt=0.0, description="Total property purchase basis")
    equity_invested: float = Field(..., gt=0.0, description="Total equity required at acquisition")
    loan_amount: float = Field(default=0.0, ge=0.0, description="Total debt financing amount")
    unlevered_irr: float = Field(..., description="Unlevered Internal Rate of Return")
    levered_irr: float = Field(..., description="Levered Internal Rate of Return to equity")
    equity_multiple: float = Field(
        ..., ge=0.0, description="Total cash distributed / equity invested"
    )
    net_present_value: float = Field(..., description="NPV of levered cash flows at discount rate")
    in_place_cap_rate: float = Field(..., ge=0.0, description="Year 1 cap rate")
    exit_cap_rate: float = Field(..., ge=0.0, description="Terminal exit cap rate applied")
    gross_exit_sales_price: float = Field(..., ge=0.0, description="Gross valuation at exit")
    net_sales_proceeds: float = Field(
        ..., description="Proceeds after disposition cost and loan payoff"
    )
    total_net_profit: float = Field(..., description="Total levered net dollar gain")
    min_dscr_observed: float = Field(
        default=0.0, ge=0.0, description="Lowest DSCR during hold period"
    )
    average_dscr: float = Field(default=0.0, ge=0.0, description="Mean DSCR across hold period")


class SensitivityScenario(BaseModel):
    """Outcome of varying rent growth and exit cap rate."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    rent_growth_delta_bps: int = Field(..., description="Rent growth adjustment in basis points")
    exit_cap_delta_bps: int = Field(..., description="Exit cap rate adjustment in basis points")
    levered_irr: float = Field(..., description="Resulting levered IRR")
    equity_multiple: float = Field(..., ge=0.0, description="Resulting Equity Multiple")
    net_present_value: float = Field(..., description="Resulting Net Present Value")


class SensitivityMatrix(BaseModel):
    """2D sensitivity analysis over key macro drivers."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    base_levered_irr: float = Field(..., description="Unshocked levered IRR")
    base_equity_multiple: float = Field(..., ge=0.0, description="Unshocked equity multiple")
    scenarios: List[SensitivityScenario] = Field(
        default_factory=list, description="Stress and upside scenario points"
    )


class DCFValuationResult(BaseEntity):
    """Complete audit-ready DCF valuation model artifact."""

    deal_id: str = Field(..., description="Associated property deal identifier")
    parameters: DCFParameters = Field(..., description="Underwriting parameters applied")
    financing: FinancingAssumptions = Field(..., description="Debt structure modeled")
    annual_cash_flows: List[AnnualCashFlow] = Field(..., description="Yearly pro-forma schedule")
    metrics: ValuationMetrics = Field(..., description="Executive return metrics")
    sensitivity: SensitivityMatrix = Field(..., description="Scenario matrix")
    model_checksum: str = Field(
        ..., description="Deterministic hash of inputs and formulas for audit trail"
    )
