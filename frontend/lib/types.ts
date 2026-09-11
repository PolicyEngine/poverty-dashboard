export type Rates = {
  all: number;
  child: number;
  working_age: number;
  senior: number;
};

export type RegionResult = {
  region_code: string;
  dataset_path: string;
  policyengine_bundle?: Record<string, unknown>;
  region_scope?: Record<string, unknown> | null;
  versions?: Versions;
  people: number;
  child_count: number;
  rates: Rates;
  deep_rates: Rates;
};

export type Versions = Record<string, string | null>;

export type Baseline = {
  generated_at: string | null;
  year: number;
  versions: Versions;
  regions: Record<string, RegionResult>;
  errors: { region_code: string; error: string }[];
};

export type CensusBenchmark = {
  population: number;
  poverty_count: number;
  rate: number;
  moe: number;
};

export type CensusEffect = {
  element: string;
  section: "addition" | "subtraction" | null;
  all: number | null;
  child: number | null;
  working_age: number | null;
  senior: number | null;
};

export type PolicyEngineSpmEffect = CensusEffect & {
  section: "addition" | "subtraction";
  variables: string[];
  supported: boolean;
  note: string;
  included_in_policyengine_net_income: boolean;
  mean_amount: number | null;
};

export type CensusStateBenchmark = {
  name: string;
  official_rate: number;
  official_count: number;
  spm_rate: number;
  spm_count: number;
  rate_difference: number | null;
};

export type CensusSpmReport = {
  report: string;
  report_year: number;
  published: string;
  sources: Record<string, string>;
  national: Record<"all" | "child" | "working_age" | "senior", CensusBenchmark>;
  threshold_ratio_distribution: {
    spm_2024: ThresholdRatioDistribution;
    source: string;
  };
  effects: CensusEffect[];
  states_3yr_2022_2024: Record<string, CensusStateBenchmark>;
};

export type SpmRateSet = Record<"all" | "child" | "working_age" | "senior", number>;

export type ThresholdRatioBinKey =
  | "less_than_0_50"
  | "from_0_50_to_0_99"
  | "from_1_00_to_1_49"
  | "from_1_50_to_1_99"
  | "from_2_00_to_3_99"
  | "from_4_00_or_more";

export type ThresholdRatioDistribution = Record<
  "all" | "child" | "working_age" | "senior",
  Record<ThresholdRatioBinKey, number>
>;

export type SpmGapCheck = SpmRateSet & {
  label: string;
  note: string;
};

export type NegativeIncomeSourceDiagnostic = {
  key: string;
  label: string;
  dataset_path: string;
  available: boolean;
  income_variable: string | null;
  person_count: number | null;
  negative_person_count: number | null;
  negative_person_share: number | null;
  spm_unit_count: number | null;
  negative_spm_unit_count: number | null;
  negative_spm_unit_share: number | null;
  negative_income_mass: number | null;
  negative_income_abs_mass: number | null;
  mean_spm_unit_income: number | null;
  mean_negative_spm_unit_income: number | null;
  minimum_spm_unit_income: number | null;
  note: string;
  error?: string;
};

export type NegativeIncomeDiagnostics = {
  title: string;
  year: number;
  income_variable_candidates: {
    enhanced_cps: string[];
    raw_cps_asec: string[];
  };
  sources: {
    enhanced_cps: NegativeIncomeSourceDiagnostic;
    raw_cps_asec: NegativeIncomeSourceDiagnostic;
  };
  comparison: {
    available: boolean;
    note: string;
    negative_person_share_difference: number | null;
    negative_person_count_difference: number | null;
    negative_income_abs_mass_difference: number | null;
    negative_income_abs_mass_ratio: number | null;
  };
  note: string;
};

export type SourceReplicationSourceDiagnostic = {
  key: string;
  label: string;
  dataset_path: string;
  available: boolean;
  resource_variable: string;
  threshold_variable: string;
  rates: SpmRateSet | null;
  population: number | null;
  mean_resource: number | null;
  median_resource: number | null;
  mean_threshold: number | null;
  threshold_ratio_distribution: ThresholdRatioDistribution | null;
  resource_distribution: ResourceDistributionDiagnostic | null;
  note: string;
  error?: string;
};

export type QuantileSummary = {
  p01: number;
  p05: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
};

export type ResourceDistributionDiagnostic = {
  resource_quantiles: QuantileSummary;
  threshold_ratio_quantiles: QuantileSummary;
  share_below_zero: number;
  share_zero_or_below: number;
  share_below_half_threshold: number;
  share_below_threshold: number;
  share_from_one_to_two_threshold: number;
  share_above_four_threshold: number;
};

export type SourceReplicationDiagnostics = {
  title: string;
  year: number;
  sources: {
    enhanced_cps: SourceReplicationSourceDiagnostic;
    raw_cps_asec: SourceReplicationSourceDiagnostic;
  };
  component_mean_gaps: {
    variable: string;
    label: string;
    available: boolean;
    enhanced_mean: number | null;
    raw_mean: number | null;
    difference: number | null;
    enhanced_below_threshold_mean: number | null;
    raw_below_threshold_mean: number | null;
    below_threshold_difference: number | null;
    error?: string;
  }[];
  note: string;
};

export type TotalIncomeLeafDiagnostics = {
  title: string;
  year: number;
  source_url: string;
  raw_person_file: string;
  leaf_columns: string[];
  ptotval_from_person_leaves: ReconstructionMetrics;
  spm_totval_from_ptotval: ReconstructionMetrics;
  spm_totval_from_person_leaves: ReconstructionMetrics;
  spm_resource_formula?: {
    title: string;
    spm_resources_from_formula: ReconstructionMetrics;
    components: RawSpmResourceFormulaComponent[];
    note: string;
  };
  component_mean_gaps: {
    key: string;
    label: string;
    raw_columns: string[];
    enhanced_variables: string[];
    raw_mean: number;
    enhanced_mean: number | null;
    difference: number | null;
    enhanced_available: boolean;
    note: string | null;
  }[];
  note: string;
};

export type RawSpmResourceFormulaComponent = {
  key: string;
  label: string;
  section: "addition" | "subtraction";
  raw_columns: string[];
  enhanced_variables: string[];
  raw_mean: number;
  enhanced_mean: number | null;
  difference: number | null;
  enhanced_available: boolean;
  note: string | null;
};

export type ReconstructionMetrics = {
  mean_abs_error: number;
  max_abs_error: number;
  exact_share: number;
  weighted_mean_abs_error: number;
  weighted_mean_error: number;
};

export type SpmGapDiagnostics = {
  generated_at: string;
  title: string;
  summary: string[];
  benchmarks: {
    census_2024_spm: CensusSpmReport["national"];
    census_2024_spm_deep: SpmRateSet & { source: string };
    policyengine_2026_committed: SpmRateSet & {
      deep_all: number;
      deep_child: number;
      people: number;
    };
  };
  gap_accounting?: {
    census_rate: number;
    policyengine_modeled_rate: number;
    policyengine_modeled_gap: number;
    modeled_plus_omitted_rate: number;
    remaining_gap_after_omitted_resources: number;
    omitted_resources_gap_closure: number;
    omitted_resources_share_of_gap: number | null;
    raw_cps_reported_rate: number | null;
    raw_cps_reported_gap: number | null;
    note: string;
  };
  policyengine_2024_checks: SpmGapCheck[];
  policyengine_2024_element_effects: PolicyEngineSpmEffect[];
  admin_calibration_targets: {
    element: string;
    variables: string[];
    source: string;
    target: string;
    implementation_note: string;
  }[];
  threshold_ratio_distribution: {
    bins: { key: ThresholdRatioBinKey; label: string }[];
    census_2024_spm: ThresholdRatioDistribution;
    policyengine_2024_modeled: ThresholdRatioDistribution;
    policyengine_2024_modeled_plus_omitted_resources: ThresholdRatioDistribution;
  };
  source_replication_diagnostics?: SourceReplicationDiagnostics;
  total_income_leaf_diagnostics?: TotalIncomeLeafDiagnostics;
  negative_income_diagnostics?: NegativeIncomeDiagnostics;
  policyengine_2024_resource_means: Record<string, number | string>;
  bls_2024_reference_thresholds: {
    two_adults_two_children: {
      renter: number;
      owner_with_mortgage: number;
      owner_without_mortgage: number;
      official_threshold: number;
    };
    note: string;
  };
  sources: Record<string, string>;
};
