import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
} from "cursor/canvas";

function MetricChart({
  title,
  unit,
  smritikosh,
  direct,
  prefix,
}: {
  title: string;
  unit: string;
  smritikosh: number;
  direct: number;
  prefix?: string;
}) {
  return (
    <Stack gap={6}>
      <Text weight="semibold">{title}</Text>
      <Text size="small" tone="secondary">
        Horizontal axis: exploration method · Vertical axis: {unit}
      </Text>
      <BarChart
        categories={["Smritikosh", "Direct filesystem"]}
        series={[{ name: title, data: [smritikosh, direct], tone: "info" }]}
        valuePrefix={prefix}
        height={210}
        showValues
      />
      <Text size="small" tone="tertiary">
        Source: embedded session timestamps and summed per-turn usage · 17 Sep 2026
      </Text>
    </Stack>
  );
}

export default function InterestComputationComparison() {
  return (
    <Stack gap={22} style={{ padding: 24, maxWidth: 1160, margin: "0 auto" }}>
      <Stack gap={8}>
        <Row justify="space-between" align="center" wrap>
          <H1>Interest computation: Smritikosh vs. direct exploration</H1>
          <Pill active>Better evidence at lower cost</Pill>
        </Row>
        <Text tone="secondary">
          Both Claude Opus 5 sessions answered “How interest is computed?” for the same statement
          billing repository. Session <Code>01a0b104…</Code> used Smritikosh and the guidance
          embedded in <Code>explore tools</Code>; session <Code>01a0b101…</Code> used native shell
          and file reads.
        </Text>
        <Callout tone="info" title="Verdict">
          Smritikosh cost 30.4% less, processed 32.5% fewer cumulative tokens, and used 40% fewer
          agent-level tool calls. It took 12.6 seconds longer, but produced the stronger answer:
          clearer evidence boundaries, one directly read test, an explicit unverified section, and
          fewer inaccurate adjacent claims.
        </Callout>
      </Stack>

      <Grid columns="minmax(0, 1.35fr) minmax(280px, 0.65fr)" gap={18}>
        <Row gap={28} align="center" wrap>
          <Stat value="−30.4%" label="Smritikosh cost" tone="success" />
          <Stat value="−32.5%" label="Token processing" tone="success" />
          <Stat value="+12.6s" label="Elapsed time" tone="warning" />
        </Row>
        <Stack gap={6}>
          <Text weight="semibold">Embedded guidance result</Text>
          <Text>10 Smritikosh processes · 8 verified files</Text>
          <Text size="small" tone="secondary">
            Mostly followed; citation and facet discipline remain incomplete
          </Text>
        </Stack>
      </Grid>

      <H2>Measured comparison</H2>
      <Table
        headers={["Metric", "Smritikosh", "Direct filesystem", "Smritikosh effect"]}
        rows={[
          ["Prompt → final answer", "68.398s", "55.816s", "12.582s slower · +22.5%"],
          ["Recorded cost", "$0.229527", "$0.329750", "$0.100223 lower · −30.4%"],
          ["Cumulative usage tokens", "85,188", "126,244", "41,056 fewer · −32.5%"],
          ["Output tokens", "3,684", "3,745", "61 fewer · −1.6%"],
          ["Cache-read tokens", "64,687", "92,082", "27,395 fewer · −29.8%"],
          ["Cache-write tokens", "16,799", "30,399", "13,600 fewer · −44.7%"],
          ["Assistant messages", "8", "8", "No change"],
          ["Agent-level tool calls", "9", "15", "6 fewer · −40.0%"],
          ["Underlying operations", "10 Smritikosh processes", "15 native calls", "Different units"],
          ["Implementation files read", "7", "9+", "Direct broader"],
          ["Test bodies read", "1", "0", "Smritikosh stronger"],
        ]}
        columnAlign={["left", "right", "right", "left"]}
        rowTone={[
          "warning",
          "success",
          "success",
          "success",
          "success",
          "success",
          undefined,
          "success",
          undefined,
          "warning",
          "success",
        ]}
        striped
      />
      <Text size="small" tone="tertiary">
        Token totals sum per-turn usage, including repeated cached context. Smritikosh stayed within
        its 12-call-after-tools budget with nine agent calls after discovery.
      </Text>

      <Grid columns={2} gap={20}>
        <MetricChart
          title="Prompt-to-answer elapsed time"
          unit="seconds"
          smritikosh={68.398}
          direct={55.816}
        />
        <MetricChart
          title="Recorded session cost"
          unit="US dollars"
          smritikosh={0.22952725}
          direct={0.32974975}
          prefix="$"
        />
      </Grid>

      <H2>Exploration behavior</H2>
      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader trailing={<Pill active size="sm">Smritikosh</Pill>}>
            Guided evidence funnel
          </CardHeader>
          <CardBody>
            <Stack gap={7}>
              <Text>
                Ran <Code>tools</Code>, three searches, and six chunk operations. It read 13 ranges
                across eight files, including the daily-compounding unit test, then separated
                verified behavior from unresolved cycle, grace-period, UBI, and SCRA paths.
              </Text>
              <Text size="small" tone="secondary">
                The run batched ranges effectively, but one search used only three facets and two
                range boundaries overlapped.
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">Direct</Pill>}>
            Filename-led source reading
          </CardHeader>
          <CardBody>
            <Stack gap={7}>
              <Text>
                Used six shell calls and nine full-file reads. It inspected more adjacent
                implementation, including configuration, minimum-interest fees, unbilled interest,
                and adjustments, but never read a test body.
              </Text>
              <Text size="small" tone="secondary">
                Discovery was efficient but lacked explicit failure/test facets, evidence-category
                tracking, and a dedicated assumptions section.
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>Answer-quality comparison</H2>
      <Table
        headers={["Dimension", "Smritikosh", "Direct filesystem", "Assessment"]}
        rows={[
          [
            "Core daily-interest formula",
            "Accurate and chunk-verified",
            "Mostly accurate and source-read",
            "Equivalent core result",
          ],
          [
            "Calculation pipeline",
            "Gate, inputs, strategy, ledger output, roll-up",
            "Similar pipeline with more adjacent variants",
            "Both useful",
          ],
          [
            "Test evidence",
            "One full unit-test body read",
            "No tests inspected",
            "Smritikosh stronger",
          ],
          [
            "Failure-path coverage",
            "Explicit gaps, but config/persistence paths missed",
            "Thin and no unknowns section",
            "Smritikosh stronger",
          ],
          [
            "Citation form",
            "Many shorthand ranges; two tests search-only",
            "Single-line, often inaccurate; no valid ranges",
            "Smritikosh stronger, still noncompliant",
          ],
          [
            "Grace-period interpretation",
            "Unverified and disclosed",
            "Claimed without evaluator body",
            "Smritikosh better calibrated",
          ],
          [
            "Minimum-interest behavior",
            "Not claimed",
            "Incorrectly described as top-up/replacement",
            "Direct answer weaker",
          ],
          [
            "Adjustment behavior",
            "Bounded to read implementation",
            "Overstated as booking a delta",
            "Smritikosh stronger",
          ],
        ]}
        rowTone={[
          "success",
          "success",
          "success",
          "warning",
          "warning",
          "info",
          "warning",
          "warning",
        ]}
        striped
      />

      <Callout tone="warning" title="Embedded guidance is working, but not fully">
        The agent read and mostly followed the <Code>tools</Code> payload: correct workflow,
        batching, call budget, implementation reads, one test body, and explicit unknowns. It still
        ignored the four-facet minimum once, reused overlapping synonyms, cited shorthand ranges,
        and presented two search-only test names as evidence.
      </Callout>

      <Callout tone="success" title="Recommended CLI-description refinement">
        Make the answer contract more mechanical: “Every citation must repeat the complete path;
        never use bare <Code>:START-END</Code>,” and “Tests count as evidence only after their body
        is returned by <Code>chunks</Code>.” Consider returning these as short mandatory rules rather
        than advisory guidance.
      </Callout>
    </Stack>
  );
}
