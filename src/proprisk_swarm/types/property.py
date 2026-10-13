"""Domain models for CRE properties, physical specs, unit mixes, and deal headers."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from proprisk_swarm.types.base import BaseEntity


class PropertyType(str, Enum):
    """Commercial Real Estate asset classes."""

    MULTIFAMILY = "multifamily"
    OFFICE = "office"
    INDUSTRIAL = "industrial"
    RETAIL = "retail"
    MIXED_USE = "mixed_use"
    HOSPITALITY = "hospitality"
    SELF_STORAGE = "self_storage"
    DATA_CENTER = "data_center"
    HEALTHCARE = "healthcare"


class DealStatus(str, Enum):
    """Pipeline progression stages for a CRE deal."""

    SOURCING = "sourcing"
    SCREENING = "screening"
    DILIGENCE = "diligence"
    UNDERWRITING = "underwriting"
    IC_REVIEW = "ic_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class PropertyAddress(BaseModel):
    """Normalized postal and parcel location details."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    street: str = Field(..., min_length=3, description="Street address line 1")
    unit_or_suite: Optional[str] = Field(
        default=None, description="Suite or building unit identifier"
    )
    city: str = Field(..., min_length=2, description="Municipality name")
    state: str = Field(..., min_length=2, max_length=2, description="Two-letter US state code")
    postal_code: str = Field(..., min_length=5, max_length=10, description="ZIP or ZIP+4 code")
    county: str = Field(..., min_length=2, description="County name for municipal recording lookup")
    apn: str = Field(..., min_length=3, description="Assessor's Parcel Number (tax ID)")
    latitude: Optional[float] = Field(
        default=None, ge=-90.0, le=90.0, description="Latitude coordinate"
    )
    longitude: Optional[float] = Field(
        default=None, ge=-180.0, le=180.0, description="Longitude coordinate"
    )

    @field_validator("state")
    @classmethod
    def normalize_state(cls, v: str) -> str:
        """Ensure state code is uppercase."""
        return v.upper().strip()

    @property
    def full_address(self) -> str:
        """Formatted one-line address string."""
        unit_str = f" {self.unit_or_suite}," if self.unit_or_suite else ","
        return f"{self.street}{unit_str} {self.city}, {self.state} {self.postal_code}"


class UnitSpec(BaseModel):
    """Specification of an individual unit tier or lease floorplan."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    unit_type: str = Field(
        ..., min_length=1, description="Floor plan or unit descriptor (e.g. '1B/1B')"
    )
    count: int = Field(..., ge=1, description="Total units of this type")
    square_feet: float = Field(
        ..., gt=0.0, description="Average net rentable square footage per unit"
    )
    in_place_rent: float = Field(
        ..., ge=0.0, description="Current monthly contractual rent per unit"
    )
    market_rent: float = Field(
        default=0.0, ge=0.0, description="Pro-forma market monthly rent per unit"
    )
    vacant_units: int = Field(
        default=0, ge=0, description="Currently unoccupied units of this type"
    )

    @model_validator(mode="before")
    @classmethod
    def _default_market_rent(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "market_rent" not in data and "in_place_rent" in data:
                data["market_rent"] = data["in_place_rent"]
        return data

    @model_validator(mode="after")
    def validate_vacancy_count(self) -> UnitSpec:
        """Verify vacant unit count does not exceed total count."""
        if self.vacant_units > self.count:
            raise ValueError(
                f"vacant_units ({self.vacant_units}) cannot exceed count ({self.count})"
            )
        return self

    @property
    def occupied_units(self) -> int:
        """Number of occupied units."""
        return self.count - self.vacant_units

    @property
    def in_place_rent_psf(self) -> float:
        """Monthly in-place rent per square foot."""
        return self.in_place_rent / self.square_feet

    @property
    def market_rent_psf(self) -> float:
        """Monthly market rent per square foot."""
        return self.market_rent / self.square_feet

    @property
    def monthly_loss_to_lease(self) -> float:
        """Monthly upside gap between market rent and in-place rent across occupied units."""
        return max(0.0, (self.market_rent - self.in_place_rent) * self.occupied_units)


class UnitMix(BaseModel):
    """Aggregated portfolio or property unit breakdown."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    items: List[UnitSpec] = Field(..., min_length=1, description="Unit type lines")

    @property
    def total_units(self) -> int:
        """Sum of all units."""
        return sum(item.count for item in self.items)

    @property
    def total_vacant_units(self) -> int:
        """Sum of vacant units across mix."""
        return sum(item.vacant_units for item in self.items)

    @property
    def physical_occupancy_rate(self) -> float:
        """Occupied units divided by total units."""
        if self.total_units == 0:
            return 0.0
        return (self.total_units - self.total_vacant_units) / self.total_units

    @property
    def total_rentable_sqft(self) -> float:
        """Total rentable square footage across all units."""
        return sum(item.count * item.square_feet for item in self.items)

    @property
    def total_in_place_monthly_rent(self) -> float:
        """Sum of monthly in-place rent for occupied units."""
        return sum(item.occupied_units * item.in_place_rent for item in self.items)

    @property
    def total_market_monthly_rent(self) -> float:
        """Sum of potential monthly market rent for all units."""
        return sum(item.count * item.market_rent for item in self.items)

    @property
    def annual_in_place_rent(self) -> float:
        """Annualized in-place rent from occupied units."""
        return self.total_in_place_monthly_rent * 12.0

    @property
    def annual_market_rent(self) -> float:
        """Annualized potential market rent across all units."""
        return self.total_market_monthly_rent * 12.0

    @property
    def weighted_average_rent_psf(self) -> float:
        """Weighted average monthly rent per square foot."""
        if self.total_rentable_sqft == 0.0:
            return 0.0
        return self.total_in_place_monthly_rent / self.total_rentable_sqft


class PropertyPhysical(BaseModel):
    """Physical and zoning attributes of the subject property."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    gross_square_feet: float = Field(..., gt=0.0, description="Gross building footprint area")
    rentable_square_feet: float = Field(..., gt=0.0, description="Net leasable area")
    year_built: int = Field(
        ..., ge=1800, le=2035, description="Initial construction completion year"
    )
    year_renovated: Optional[int] = Field(
        default=None, ge=1800, le=2035, description="Year of major capital renovation"
    )
    site_area_acres: float = Field(..., gt=0.0, description="Land parcel size in acres")
    stories: int = Field(default=1, ge=1, description="Building height in stories")
    parking_spaces: int = Field(default=0, ge=0, description="Total designated parking spaces")
    zoning_code: str = Field(
        default="COMMERCIAL", min_length=1, description="Municipal zoning classification"
    )
    flood_zone: str = Field(default="X", min_length=1, description="FEMA flood hazard designation")

    @model_validator(mode="after")
    def validate_physical_consistency(self) -> PropertyPhysical:
        """Ensure rentable square feet does not exceed gross building size."""
        if self.rentable_square_feet > self.gross_square_feet:
            raise ValueError(
                f"rentable_square_feet ({self.rentable_square_feet}) cannot exceed gross_square_feet ({self.gross_square_feet})"
            )
        if self.year_renovated is not None and self.year_renovated < self.year_built:
            raise ValueError(
                f"year_renovated ({self.year_renovated}) cannot precede year_built ({self.year_built})"
            )
        return self


class OperatingExpenses(BaseModel):
    """Itemized annual operational expenditures."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    property_taxes: float = Field(
        default=0.0, ge=0.0, description="Ad valorem municipal property taxes"
    )
    insurance: float = Field(
        default=0.0, ge=0.0, description="Property and casualty hazard insurance"
    )
    utilities: float = Field(
        default=0.0, ge=0.0, description="Common area water, power, gas, trash"
    )
    repairs_maintenance: float = Field(
        default=0.0, ge=0.0, description="Routine maintenance and turnover"
    )
    management_fees: float = Field(
        default=0.0, ge=0.0, description="Third-party property management fees"
    )
    payroll: float = Field(default=0.0, ge=0.0, description="On-site leasing and maintenance staff")
    marketing_leasing: float = Field(
        default=0.0, ge=0.0, description="Advertising, showings, commissions"
    )
    general_admin: float = Field(
        default=0.0, ge=0.0, description="Legal, accounting, software, bank fees"
    )
    capex_reserve: float = Field(
        default=0.0, ge=0.0, description="Annual replacement reserve allocation"
    )

    @property
    def total_opex(self) -> float:
        """Sum of all operational expenditure line items."""
        return (
            self.property_taxes
            + self.insurance
            + self.utilities
            + self.repairs_maintenance
            + self.management_fees
            + self.payroll
            + self.marketing_leasing
            + self.general_admin
            + self.capex_reserve
        )

    def opex_ratio(self, effective_gross_income: float) -> float:
        """Calculate operational expense ratio relative to effective gross income."""
        if effective_gross_income <= 0.0:
            return 0.0
        return self.total_opex / effective_gross_income


class HistoricalFinancials(BaseModel):
    """Historical or trailing-twelve-month (T12) operating performance."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    period_label: str = Field(..., min_length=1, description="Period name (e.g. 'T12', '2025A')")
    gross_potential_rent: float = Field(
        ..., ge=0.0, description="Total potential contractual income"
    )
    vacancy_credit_loss: float = Field(
        default=0.0, ge=0.0, description="Physical vacancy and uncollected rent"
    )
    concessions: float = Field(
        default=0.0, ge=0.0, description="Tenant rental discounts and abatements"
    )
    other_income: float = Field(
        default=0.0, ge=0.0, description="Ancillary fees (parking, storage, laundry, pet)"
    )
    expenses: OperatingExpenses = Field(..., description="Itemized operating expenses")

    @property
    def effective_gross_income(self) -> float:
        """Calculated effective revenue collected."""
        return max(
            0.0,
            self.gross_potential_rent
            - self.vacancy_credit_loss
            - self.concessions
            + self.other_income,
        )

    @property
    def net_operating_income(self) -> float:
        """Net operating income after operating expenses."""
        return self.effective_gross_income - self.expenses.total_opex


class PropertyDeal(BaseEntity):
    """Primary commercial real estate deal record under diligence."""

    title: str = Field(..., min_length=3, description="Deal or property marketing name")
    property_type: PropertyType = Field(..., description="Target property asset classification")
    status: DealStatus = Field(default=DealStatus.SOURCING, description="Current workflow state")
    address: PropertyAddress = Field(..., description="Physical and municipal address")
    physical: PropertyPhysical = Field(
        ..., description="Building architecture and structural dimensions"
    )
    unit_mix: UnitMix = Field(..., description="Floorplan and lease mix inventory")
    asking_price: float = Field(..., gt=0.0, description="Seller offering price")
    target_purchase_price: float = Field(..., gt=0.0, description="Proposed acquisition basis")
    in_place_noi: float = Field(..., description="Current in-place Net Operating Income")
    sponsor_name: str = Field(..., min_length=2, description="Target borrower or equity sponsor")
    broker_name: Optional[str] = Field(
        default=None, description="Listing investment sales brokerage"
    )
    target_closing_date: Optional[date] = Field(
        default=None, description="Expected purchase closing date"
    )
    historical_financials: List[HistoricalFinancials] = Field(
        default_factory=list, description="Trailing financial periods"
    )

    @property
    def asking_cap_rate(self) -> float:
        """Cap rate based on in-place NOI and seller asking price."""
        if self.asking_price <= 0.0:
            return 0.0
        return self.in_place_noi / self.asking_price

    @property
    def target_cap_rate(self) -> float:
        """Cap rate based on in-place NOI and target purchase price."""
        if self.target_purchase_price <= 0.0:
            return 0.0
        return self.in_place_noi / self.target_purchase_price

    @property
    def in_place_cap_rate(self) -> float:
        """Alias for target_cap_rate representing in-place acquisition yield."""
        return self.target_cap_rate

    @property
    def price_per_unit(self) -> float:
        """Target acquisition basis per residential or commercial unit."""
        if self.unit_mix.total_units == 0:
            return 0.0
        return self.target_purchase_price / self.unit_mix.total_units

    @property
    def price_per_sqft(self) -> float:
        """Target acquisition basis per rentable square foot."""
        if self.physical.rentable_square_feet == 0.0:
            return 0.0
        return self.target_purchase_price / self.physical.rentable_square_feet

