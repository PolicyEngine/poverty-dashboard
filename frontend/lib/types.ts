export type Rates = {
  all: number;
  child: number;
  working_age: number;
  senior: number;
};

export type RegionResult = {
  region_code: string;
  dataset_path: string;
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
  note: string;
  error?: string;
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
    error?: string;
  }[];
  note: string;
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
