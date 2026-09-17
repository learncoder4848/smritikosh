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
        Horizontal axis: loading method · Vertical axis: {unit}
      </Text>
      <BarChart
        categories={["Smritikosh", "Selective file loading"]}
        series={[{ name: title, data: [smritikosh, direct], tone: "info" }]}
        valuePrefix={prefix}
        height={210}
        showValues
      />
      <Text size="small" tone="tertiary">
        Source: embedded session timestamps and summed per-turn usage · 16 Sep 2026
      </Text>
    </Stack>
  );
}

export default function IbizaSmritikoshVsSelectiveLoading() {
  return (
    <Stack gap={22} style={{ padding: 24, maxWidth: 1160, margin: "0 auto" }}>
      <Stack gap={8}>
        <Row justify="space-between" align="center" wrap>
          <H1>Ibiza discovery: Smritikosh vs. selective file loading</H1>
          <Pill active>Smritikosh wins efficiency and citation reliability</Pill>
        </Row>
        <Text tone="secondary">
          Both sessions investigated changing an account’s <Code>product_id</Code> while preserving
          identity and history. The Smritikosh run queried an index of 50 curated system documents;
          the comparison run selected and read those documents directly.
        </Text>
        <Callout tone="info" title="Verdict">
          Smritikosh finished 50.3% faster, cost 71.3% less, and processed 80.4% fewer cumulative
          tokens. Neither run verified implementation source or tests, so both remain architecture
          discovery rather than implementation proof. The direct run named more confirmed systems,
          but most of its cited ranges did not support their attached claims.
        </Callout>
      </Stack>

      <Grid columns="minmax(0, 1.35fr) minmax(280px, 0.65fr)" gap={18}>
        <Row gap={28} align="center" wrap>
          <Stat value="56.6s" label="Smritikosh duration" tone="success" />
          <Stat value="−71.3%" label="Cost" tone="success" />
          <Stat value="−80.4%" label="Token processing" tone="success" />
        </Row>
        <Stack gap={6}>
          <Text weight="semibold">Evidence boundary</Text>
          <Text>Indexed docs vs. directly read docs</Text>
          <Text size="small" tone="secondary">
            No service repositories, source contracts, or tests were checked
          </Text>
        </Stack>
      </Grid>

      <H2>Measured comparison</H2>
      <Table
        headers={["Metric", "Smritikosh", "Selective loading", "Smritikosh effect"]}
        rows={[
          ["User → final entry", "56.581s", "113.864s", "57.283s faster · −50.3%"],
          ["Recorded cost", "$0.360990", "$1.259074", "$0.898084 lower · −71.3%"],
          ["Cumulative usage tokens", "133,061", "677,484", "544,423 fewer · −80.4%"],
          ["Output tokens", "3,371", "8,542", "5,171 fewer · −60.5%"],
          ["Cache-read tokens", "92,840", "545,275", "452,435 fewer · −83.0%"],
          ["Cache-write tokens", "36,836", "123,641", "86,805 fewer · −70.2%"],
          ["Assistant messages", "6", "12", "6 fewer · −50.0%"],
          ["Agent-level tool calls", "6", "18", "12 fewer · −66.7%"],
          ["Knowledge files retrieved", "17 indexed files", "8 directly read files", "Different selection"],
          ["Final answer length", "592 words", "598 words", "Essentially equal"],
          ["Confirmed / possible systems", "5 / 6", "8 / 6", "Direct classified more confirmed"],
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
          "success",
          undefined,
          undefined,
          "warning",
        ]}
        striped
      />
      <Text size="small" tone="tertiary">
        Token totals sum per-turn usage and repeated cached context. Smritikosh made four indexed
        exploration calls; selective loading used eleven file reads plus discovery shell commands.
      </Text>

      <Grid columns={2} gap={20}>
        <MetricChart
          title="User-to-final elapsed time"
          unit="seconds"
          smritikosh={56.581}
          direct={113.864}
        />
        <MetricChart
          title="Recorded session cost"
          unit="US dollars"
          smritikosh={0.36099}
          direct={1.25907375}
          prefix="$"
        />
      </Grid>

      <H2>Investigation behavior</H2>
      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader trailing={<Pill active size="sm">Smritikosh</Pill>}>
            Indexed retrieval
          </CardHeader>
          <CardBody>
            <Stack gap={7}>
              <Text>
                One six-facet discovery pass produced 28 candidates, followed by 18 selected ranges
                across 17 files and a targeted evidence pass returning nine chunks across seven
                files.
              </Text>
              <Text size="small" tone="secondary">
                The result was compact and line-bounded, but heavily dependent on one dense Account
                document and did not independently validate underlying services.
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">Direct</Pill>}>
            Curated file selection
          </CardHeader>
          <CardBody>
            <Stack gap={7}>
              <Text>
                The run measured 50 knowledge files, selected 14 systems, directly read eight system
                documents, and left six as possible. It also wrote the skill-required loading trace.
              </Text>
              <Text size="small" tone="secondary">
                More context was loaded, but line-number drift caused 14 of 18 unique cited ranges
                to be plainly mismatched.
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>Answer-quality comparison</H2>
      <Table
        headers={["Dimension", "Smritikosh", "Selective loading", "Assessment"]}
        rows={[
          [
            "Core ownership model",
            "Account owner; Card, Ledger, Statement Billing downstream",
            "Similar model with eight confirmed systems",
            "Broadly aligned",
          ],
          [
            "Identity/history preservation",
            "Not established",
            "Not established",
            "Shared critical gap",
          ],
          [
            "Citation coverage",
            "All system rows and findings cited",
            "24 citations across 18 ranges",
            "Both superficially complete",
          ],
          [
            "Citation accuracy",
            "Bounded indexed excerpts; some inference",
            "14 of 18 unique ranges mismatched",
            "Smritikosh stronger",
          ],
          [
            "System classification",
            "Card and Program Config overclassified",
            "Several claims exceed documents",
            "Neither fully reliable",
          ],
          [
            "Propagation and ordering",
            "Plausible, not end-to-end verified",
            "Exactly-two-consumers claim unsupported",
            "Shared evidence gap",
          ],
          [
            "Source and test verification",
            "None",
            "None",
            "Equivalent limitation",
          ],
          [
            "Prompt-format adherence",
            "Mostly compliant; minor tool deviations",
            "Strong limits and structure",
            "Direct structurally stronger",
          ],
        ]}
        rowTone={[
          "success",
          "warning",
          undefined,
          "success",
          "warning",
          "warning",
          "warning",
          undefined,
        ]}
        striped
      />

      <Callout tone="warning" title="What neither session proved">
        Neither established the initiating API and authorization contract, stable account identity,
        prior-product history semantics, complete consumer coverage, reconciliation behavior, event
        ordering, or implementation-level test coverage.
      </Callout>

      <Callout tone="success" title="Recommended use">
        Prefer Smritikosh for the discovery phase, then require targeted source and test verification
        for the write contract, identity/history invariants, event consumers, idempotency, and
        downstream reconciliation before treating any system as confirmed.
      </Callout>
    </Stack>
  );
}
