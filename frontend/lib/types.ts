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
