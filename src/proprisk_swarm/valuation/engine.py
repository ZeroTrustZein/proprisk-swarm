"""Valuation Engine subsystem for DCF modeling, IRR calculation, and memo synthesis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from proprisk_swarm.protocols import ValuationEngineProtocol
from proprisk_swarm.types.financial import SensitivityMatrix, ValuationMetrics
from proprisk_swarm.types.risk import MemoRecommendation, UnderwritingMemo


class ValuationEngine(ValuationEngineProtocol):
    """Multi-year DCF valuation solver and Investment Committee memo synthesizer."""

    def _calculate_irr(self, cash_flows: List[float], max_iter: int = 100) -> float:
        """Robust IRR solver using bisection method."""
        if not cash_flows or len(cash_flows) < 2:
            return 0.0

        low = -0.999
        high = 5.0

        def npv_at(rate: float) -> float:
            val = 0.0
            for t, cf in enumerate(cash_flows):
                val += cf / ((1.0 + rate) ** t)
            return val

        f_low = npv_at(low)
        f_high = npv_at(high)

        if f_low * f_high > 0:
            # Fall back to approximate yield
            total_profit = sum(cash_flows[1:]) - abs(cash_flows[0])
            years = len(cash_flows) - 1
            return round(max(0.0, total_profit / (abs(cash_flows[0]) * max(years, 1))), 4)

        for _ in range(max_iter):
            mid = (low + high) / 2.0
            f_mid = npv_at(mid)
            if abs(f_mid) < 1e-6:
                return round(mid, 4)
            if f_low * f_mid < 0:
                high = mid
                f_high = f_mid
            else:
                low = mid
                f_low = f_mid

        return round((low + high) / 2.0, 4)

    def compute_dcf(
        self,
        purchase_price: float,
        cash_flows: List[float],
        discount_rate: float = 0.085,
        terminal_cap_rate: float = 0.0575,
    ) -> Dict[str, Any]:
        """Calculate institutional DCF metrics: NPV, Unlevered IRR, Levered IRR, Equity Multiple."""
        p_price = float(purchase_price)
        cfs = [float(cf) for cf in cash_flows]
        t_cap = max(float(terminal_cap_rate), 0.01)
        d_rate = max(float(discount_rate), 0.001)

        last_cf = cfs[-1] if cfs else p_price * 0.05
        exit_valuation = round(last_cf / t_cap, 2)
        gross_sales = exit_valuation
        net_sales = round(gross_sales * 0.98, 2)  # 2% transaction costs

        # Stream of cash flows: Year 0 = -purchase_price, Year N includes net sales proceeds
        full_stream = [-p_price] + cfs[:-1] + [cfs[-1] + net_sales]

        # NPV
        npv = sum(cf / ((1.0 + d_rate) ** t) for t, cf in enumerate(full_stream))

        # Unlevered IRR
        unlevered_irr = self._calculate_irr(full_stream)

        # Equity multiple = Total inflows / Initial equity
        total_inflows = sum(cfs[:-1]) + cfs[-1] + net_sales
        equity_mult = round(total_inflows / max(p_price, 1.0), 3)

        # Levered metrics (assuming 65% LTV senior debt at 6.0% interest)
        debt_amount = p_price * 0.65
        equity_amount = p_price * 0.35
        annual_debt_service = debt_amount * 0.065
        levered_cfs = [max(0.0, cf - annual_debt_service) for cf in cfs]
        debt_payoff = debt_amount * 0.90  # 10% amortized
        levered_stream = [-equity_amount] + levered_cfs[:-1] + [levered_cfs[-1] + (net_sales - debt_payoff)]
        levered_irr = self._calculate_irr(levered_stream)

        dscr = round(cfs[0] / max(annual_debt_service, 1.0), 2)
        debt_yield = round(cfs[0] / max(debt_amount, 1.0), 4)

        return {
            "purchase_price": p_price,
            "discount_rate": d_rate,
            "terminal_cap_rate": t_cap,
            "exit_valuation": exit_valuation,
            "gross_sales_proceeds": gross_sales,
            "net_sales_proceeds": net_sales,
            "npv": round(npv, 2),
            "unlevered_irr": unlevered_irr,
            "levered_irr": levered_irr,
            "equity_multiple": equity_mult,
            "debt_service_coverage_ratio": dscr,
            "debt_yield": debt_yield,
        }

    def compute_sensitivity_matrix(
        self,
        purchase_price: float,
        base_cash_flows: List[float],
        cap_rates: Optional[List[float]] = None,
        noi_growth_rates: Optional[List[float]] = None,
    ) -> SensitivityMatrix:
        """Generate 2D IRR sensitivity table across terminal cap rates and NOI growth variations."""
        cap_list = cap_rates or [0.050, 0.055, 0.060, 0.065]
        growth_list = noi_growth_rates or [0.01, 0.02, 0.03, 0.04]

        grid: List[List[float]] = []
        for g in growth_list:
            row: List[float] = []
            adjusted_cfs = [cf * ((1.0 + g) ** i) for i, cf in enumerate(base_cash_flows)]
            for cap in cap_list:
                res = self.compute_dcf(purchase_price, adjusted_cfs, terminal_cap_rate=cap)
                row.append(res["unlevered_irr"])
            grid.append(row)

        base_res = self.compute_dcf(purchase_price, base_cash_flows)
        return SensitivityMatrix(
            base_irr=base_res["unlevered_irr"],
            exit_cap_rates=cap_list,
            rent_growth_rates=growth_list,
            grid=grid,
        )

    def synthesize_investment_memo(
        self, deal_id: str, valuation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize audit-ready Investment Committee underwriting memo."""
        irr = valuation_data.get("unlevered_irr", 0.08)
        em = valuation_data.get("equity_multiple", 1.5)
        dscr = valuation_data.get("debt_service_coverage_ratio", 1.4)

        if irr >= 0.12 and em >= 1.6 and dscr >= 1.25:
            rec = MemoRecommendation.APPROVED
            risk_score = 25.0
            status_text = "Strong risk-adjusted profile exceeding target underwriting hurdle rates."
        elif irr >= 0.08 and dscr >= 1.15:
            rec = MemoRecommendation.CONDITIONAL_APPROVAL
            risk_score = 45.0
            status_text = "Meets baseline criteria; requires additional reserves and loan covenant monitoring."
        else:
            rec = MemoRecommendation.REJECTED
            risk_score = 75.0
            status_text = "Fails minimum return hurdle or inadequate debt service coverage."

        memo = UnderwritingMemo(
            deal_id=deal_id,
            title=valuation_data.get("deal_title", f"Underwriting Diligence: {deal_id}"),
            recommendation=rec,
            executive_summary=f"Diligence review for deal {deal_id}. {status_text}",
            overall_risk_score=risk_score,
            valuation_metrics=ValuationMetrics(
                net_present_value=valuation_data.get("npv", 0.0),
                unlevered_irr=irr,
                levered_irr=valuation_data.get("levered_irr", irr * 1.3),
                equity_multiple=em,
                exit_valuation=valuation_data.get("exit_valuation", 0.0),
                net_operating_income_terminal=valuation_data.get("net_sales_proceeds", 0.0) * 0.05,
                gross_sales_proceeds=valuation_data.get("gross_sales_proceeds", 0.0),
                net_sales_proceeds=valuation_data.get("net_sales_proceeds", 0.0),
                debt_service_coverage_ratio=dscr,
                debt_yield=valuation_data.get("debt_yield", 0.09),
            ),
        )
        return memo.model_dump()
