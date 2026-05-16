"use client";

import type {
  CensusSpmReport,
  PolicyEngineSpmEffect,
  SpmGapDiagnostics,
} from "@/lib/types";

function pp(x: number | null): string {
  if (x === null || Number.isNaN(x)) return "—";
  return `${(x * 100).toFixed(2)} pp`;
}

type JoinedEffect = {
  element: string;
  section: "addition" | "subtraction";
  census: CensusSpmReport["effects"][number] | null;
  policyengine: PolicyEngineSpmEffect | null;
};

function joinEffects(
  census: CensusSpmReport,
  policyengineEffects: PolicyEngineSpmEffect[],
  section: "addition" | "subtraction",
): JoinedEffect[] {
  const peByElement = new Map(
    policyengineEffects
      .filter((effect) => effect.section === section)
      .map((effect) => [effect.element, effect]),
  );
  const censusRows = census.effects.filter((effect) => effect.section === section);
  const rows = censusRows.map((effect) => ({
    element: effect.element,
    section,
    census: effect,
    policyengine: peByElement.get(effect.element) ?? null,
  }));
  const censusElements = new Set(censusRows.map((effect) => effect.element));
  const policyEngineOnlyRows = policyengineEffects
    .filter(
      (effect) =>
        effect.section === section && !censusElements.has(effect.element),
    )
    .map((effect) => ({
      element: effect.element,
      section,
      census: null,
      policyengine: effect,
    }));

  return [...rows, ...policyEngineOnlyRows];
}

function effectGap(
  census: CensusSpmReport["effects"][number] | null,
  policyengine: PolicyEngineSpmEffect | null,
): number | null {
  if (census?.all === null || census?.all === undefined) return null;
  if (policyengine?.all === null || policyengine?.all === undefined) return null;
  return policyengine.all - census.all;
}

export function CensusEffects({
  census,
  diagnostics,
}: {
  census: CensusSpmReport | null;
  diagnostics: SpmGapDiagnostics | null;
}) {
  if (!census) return null;

  const policyengineEffects = diagnostics?.policyengine_2024_element_effects ?? [];
  const additions = joinEffects(census, policyengineEffects, "addition");
  const subtractions = joinEffects(census, policyengineEffects, "subtraction");
  const groups = [
    { label: "Additions", rows: additions },
    { label: "Subtractions", rows: subtractions },
  ];

  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold text-secondary-900">
          SPM element effects
        </h2>
        <span className="text-xs text-secondary-500">
          2024 Census vs PolicyEngine, percentage-point effects
        </span>
      </div>
      <div className="space-y-4">
        {groups.map(({ label, rows }) => (
          <div
            key={label}
            className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm"
          >
            <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3 text-sm font-semibold text-secondary-900">
              {label}
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-white">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Element
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Census all
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      PE all
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Gap
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Census child
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      PE child
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Census 65+
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      PE 65+
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-200">
                  {rows.map((row) => {
                    const gap = effectGap(row.census, row.policyengine);
                    return (
                      <tr key={row.element}>
                        <td className="px-4 py-2">
                          <div className="font-medium text-secondary-900">
                            {row.element}
                          </div>
                          {row.policyengine?.note && (
                            <div className="max-w-sm text-xs text-secondary-500">
                              {row.policyengine.note}
                            </div>
                          )}
                          {row.policyengine?.supported &&
                            !row.policyengine.included_in_policyengine_net_income && (
                              <div className="max-w-sm text-xs font-medium text-error">
                                Upstream PE SPM resource formula omits this component.
                              </div>
                            )}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {pp(row.census?.all ?? null)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {pp(row.policyengine?.all ?? null)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums font-medium">
                          {pp(gap)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {pp(row.census?.child ?? null)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {pp(row.policyengine?.child ?? null)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {pp(row.census?.senior ?? null)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {pp(row.policyengine?.senior ?? null)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
