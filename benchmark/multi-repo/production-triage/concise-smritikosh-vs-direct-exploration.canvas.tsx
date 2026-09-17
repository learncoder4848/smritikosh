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

function ComparisonChart({
  title,
  unit,
  values,
  prefix,
}: {
  title: string;
  unit: string;
  values: [number, number];
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
        series={[{ name: title, data: values, tone: "info" }]}
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

export default function ConciseSmritikoshVsDirectExploration() {
  return (
    <Stack gap={22} style={{ padding: 24, maxWidth: 1160, margin: "0 auto" }}>
      <Stack gap={8}>
        <Row justify="space-between" align="center" wrap>
          <H1>Concise Smritikosh vs. direct repository exploration</H1>
          <Pill active>Efficiency win, breadth trade-off</Pill>
        </Row>
        <Text tone="secondary">
          Smritikosh session <Code>01a0b0ec…</Code> used the concise generic prompt. Direct session{" "}
          <Code>01a0b0c4…</Code> explored five repositories through shell and file reads. Both used
          Claude Opus 5.
        </Text>
        <Callout tone="info" title="Verdict">
          Smritikosh preserved the central diagnosis while finishing 45.6% faster, costing 76.7%
          less, and processing 90.0% fewer cumulative tokens. Direct exploration produced the more
          complete end-to-end ownership map, but its citation discipline and test verification were
          still weak relative to its much higher cost.
        </Callout>
      </Stack>

      <Grid columns="minmax(0, 1.35fr) minmax(280px, 0.65fr)" gap={18}>
        <Row gap={28} align="center" wrap>
          <Stat value="−88.1s" label="Smritikosh time" tone="success" />
          <Stat value="−76.7%" label="Smritikosh cost" tone="success" />
          <Stat value="−90.0%" label="Token processing" tone="success" />
        </Row>
        <Stack gap={6}>
          <Text weight="semibold">Coverage difference</Text>
          <Text>3 repositories vs. all 5</Text>
          <Text size="small" tone="secondary">
            Direct exploration closed several upstream and routing gaps
          </Text>
        </Stack>
      </Grid>

      <H2>Measured comparison</H2>
      <Table
        headers={["Metric", "Smritikosh", "Direct filesystem", "Smritikosh effect"]}
        rows={[
          ["Prompt → final answer", "105.269s", "193.398s", "88.129s faster · −45.6%"],
          ["Recorded cost", "$0.381101", "$1.634086", "$1.252985 lower · −76.7%"],
          ["Cumulative usage tokens", "172,758", "1,733,399", "1,560,641 fewer · −90.0%"],
          ["Output tokens", "5,036", "11,283", "6,247 fewer · −55.4%"],
          ["Cache-read tokens", "137,919", "1,636,719", "1,498,800 fewer · −91.6%"],
          ["Assistant messages", "10", "31", "21 fewer · −67.7%"],
          ["Agent-level tool calls", "15", "49", "34 fewer · −69.4%"],
          ["Underlying operations", "19 CLI invocations", "76 FS accesses", "Different abstractions"],
          ["Repositories examined", "3", "5", "Direct broader"],
          ["Directly verified files", "13", "Not reliably countable", "Export methods differ"],
        ]}
        columnAlign={["left", "right", "right", "left"]}
        rowTone={[
          "success",
          "success",
          "success",
          "success",
          "success",
          "success",
          "success",
          undefined,
          "warning",
          undefined,
        ]}
        striped
      />
      <Text size="small" tone="tertiary">
        “Filesystem accesses” expands shell loops and commands; it is not directly equivalent to a
        Smritikosh CLI invocation. Token totals include repeated cached context.
      </Text>

      <Grid columns={2} gap={20}>
        <ComparisonChart
          title="Prompt-to-answer elapsed time"
          unit="seconds"
          values={[105.269, 193.398]}
        />
        <ComparisonChart
          title="Recorded session cost"
          unit="US dollars"
          values={[0.38110075, 1.63408575]}
          prefix="$"
        />
      </Grid>

      <H2>Answer-quality comparison</H2>
      <Table
        headers={["Dimension", "Smritikosh", "Direct filesystem", "Assessment"]}
        rows={[
          [
            "Central PDF suppression gate",
            "Implementation and tests read",
            "Implementation and tests read",
            "Equivalent",
          ],
          [
            "PDF upload and ready-event path",
            "Directly verified",
            "Directly verified",
            "Equivalent",
          ],
          [
            "Cron and cycle eligibility",
            "Not inspected",
            "Predicates and product configuration inspected",
            "Direct stronger",
          ],
          [
            "Completion-event publisher",
            "Claimed, then marked unread",
            "Publisher call inspected",
            "Direct stronger",
          ],
          [
            "Account and ledger roles",
            "No account source; no ledger source",
            "Both repositories inspected",
            "Direct stronger, but ownership overstated",
          ],
          [
            "Notification routing and blockers",
            "Partial handler evidence; factory test unread",
            "Factory, status/reason, and template paths inspected",
            "Direct stronger",
          ],
          [
            "Tests proving behavior",
            "Four test files directly read",
            "Many tests found, fewer bodies read",
            "Mixed",
          ],
          [
            "Citation discipline",
            "Many shorthand and two unread citations",
            "Mostly shorthand; approximate line references",
            "Neither meets requirement",
          ],
          [
            "Uncertainty handling",
            "Explicit assumptions and unverified section",
            "No dedicated confidence section",
            "Smritikosh stronger",
          ],
        ]}
        rowTone={[
          "success",
          "success",
          "warning",
          "warning",
          "warning",
          "warning",
          undefined,
          "warning",
          "info",
        ]}
        striped
      />

      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader trailing={<Pill active size="sm">Smritikosh</Pill>}>
            Best for routine triage
          </CardHeader>
          <CardBody>
            <Text>
              It found the decisive zero-balance/no-ledger gate, PDF early return, upload path, and
              ready-event behavior at roughly one quarter of the cost. A few targeted follow-up
              reads could close most remaining gaps.
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">Direct</Pill>}>
            Best for exhaustive breadth
          </CardHeader>
          <CardBody>
            <Text>
              It inspected all five repositories and traced more upstream and downstream behavior,
              but used 10× the token processing and still overstated preference evidence and several
              test-name-only findings.
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <Callout tone="warning" title="Shared quality issue">
        Neither answer proved notification preference opt-out behavior. Both inferred more than the
        read implementation and positive test justified. The direct run also treated discovered test
        names as proof, while the Smritikosh run cited two ranges it had not read.
      </Callout>

      <Callout tone="success" title="Recommended workflow">
        Use the concise Smritikosh prompt first, then require focused gap-closing reads for upstream
        eligibility, the actual publisher, factory routing, and notification negative paths. This
        should approach the direct run’s useful coverage without paying its 4.29× cost.
      </Callout>
    </Stack>
  );
}
