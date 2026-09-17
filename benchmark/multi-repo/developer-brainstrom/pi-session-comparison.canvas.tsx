import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

const expected = [
  "prc-statement-billing-svc",
  "plt-statement-svc",
  "plt-account-svc",
  "plt-notfication-svc",
];

const session1Files = [
  "plt-statement-svc/core/statement/statement_pdf_generator.py",
  "plt-statement-svc/core/handlers/statements/statement_billing_completed_handler.py",
  "plt-statement-svc/common/utils.py",
  "plt-statement-svc/tests/core/statement/test_statement_pdf_generator.py",
  "plt-statement-svc/tests/core/handlers/statements/test_statement_billing_completed_handler.py",
  "prc-statement-billing-svc/core/common/statement_eligibility.py",
  "prc-statement-billing-svc/core/cron/statement_summary_event_generator.py",
  "prc-statement-billing-svc/core/events/handlers/account/scra_apr_change_handler.py",
  "prc-statement-billing-svc/core/computation/processor/statement/statement_processor.py",
  "prc-statement-billing-svc/core/computation/processor/statement/statement_preprocessor.py",
  "plt-notification-svc/core/events/handlers/statement/statement_summary_ready_handler.py",
  "plt-notification-svc/tests/core/events/handlers/statement/test_statement_summary_ready_handler.py",
  "plt-notification-svc/core/utils/notification_tenant_mappings.py",
];

const session2FileGroups = [
  ["prc-statement-billing-svc", "7 code files + 2 memory/reference files"],
  ["plt-statement-svc", "6 code/test files"],
  ["plt-notification-svc", "3 code files + 1 AI reference file"],
  ["plt-account-svc", "1 code file"],
  ["prc-ledger-svc", "1 incident runbook + 1 repository-local skill"],
];

function MetricChart({
  title,
  values,
  unit,
  caption,
}: {
  title: string;
  values: number[];
  unit: string;
  caption: string;
}) {
  return (
    <Stack gap={6}>
      <H3>{title}</H3>
      <Text size="small" tone="secondary">
        Horizontal axis: approach · Vertical axis: {unit}
      </Text>
      <BarChart
        categories={["Smritikosh", "Without Smritikosh"]}
        series={[{ name: unit, data: values }]}
        height={220}
        showValues
      />
      <Text size="small" tone="tertiary">{caption}</Text>
    </Stack>
  );
}

export default function SessionComparison() {
  const theme = useHostTheme();
  return (
    <Stack gap={20} style={{ padding: 24, maxWidth: 1180, margin: "0 auto" }}>
      <Stack gap={8}>
        <Row align="center" justify="space-between" wrap>
          <H1>Pi session comparison</H1>
          <Pill active>Smritikosh wins overall</Pill>
        </Row>
        <Text tone="secondary">
          Evaluation target: identify the four expected impacted services while staying evidence-based,
          direct, and efficient.
        </Text>
        <Callout tone="success" title="Verdict">
          Smritikosh exactly matched the expected impacted set (F1 1.00) while using 72.5% less cost,
          83.9% fewer tokens, and 74.3% less active time. Without Smritikosh found stronger test evidence,
          but added <Code>prc-ledger-svc</Code> as a false positive.
        </Callout>
      </Stack>

      <Grid columns="minmax(0, 1.3fr) minmax(260px, 0.7fr)" gap={16}>
        <Stack gap={10}>
          <H2>Expected impact set</H2>
          <Text size="small" tone="secondary">
            The expected spelling <Code>plt-notfication-svc</Code> is treated as the same repository as
            the answers' <Code>plt-notification-svc</Code>.
          </Text>
          <Row gap={8} wrap>
            {expected.map((service) => <span key={service}><Pill active>{service}</Pill></span>)}
          </Row>
        </Stack>
        <Row gap={24} align="center" justify="end" wrap>
          <Stat value="1.00" label="Smritikosh F1" tone="success" />
          <Stat value="0.889" label="Without Smritikosh F1" tone="warning" />
          <Stat value="72.5%" label="Cost saved with Smritikosh" tone="success" />
        </Row>
      </Grid>

      <H2>Measured comparison</H2>
      <Table
        headers={["Metric", "Smritikosh", "Without Smritikosh", "Difference"]}
        rows={[
          ["Active task time", "2m 13s", "8m 39s", "74.3% less · 3.89× faster"],
          ["Header-to-last-entry", "3m 13s", "8m 51s", "63.7% less · no explicit end marker"],
          ["Tool calls / results", "20 / 20", "43 / 43", "53.5% fewer calls · all succeeded"],
          ["Read-like operations", "17", "25", "32.0% fewer · indexed chunks vs cat/sed"],
          ["Unique files read", "13", "22", "40.9% fewer files"],
          ["Requested ranged lines", "≤1.15K (1,154)", "≤2.08K (2,076)", "44.4% fewer · full/outline excluded"],
          ["Total tokens", "502K (502,202)", "3.11M (3,114,844)", "83.9% fewer · 6.20× difference"],
          ["Grand cost", "0.674 (0.673606)", "2.45 (2.451070)", "72.5% less · 3.64× difference"],
          ["Correct expected services", "4 / 4", "4 / 4", "Equal recall"],
          ["False positives", "0", "1: prc-ledger-svc", "Smritikosh has better precision"],
          ["Precision / recall / F1", "100% / 100% / 100%", "80% / 100% / 88.9%", "20 percentage-point precision gain"],
        ]}
        rowTone={["success", undefined, "success", undefined, undefined, undefined, "success", "success", undefined, "danger", "success"]}
        striped
      />

      <Grid columns={2} gap={20}>
        <MetricChart
          title="Total tokens by approach"
          values={[0.502202, 3.114844]}
          unit="million tokens"
          caption="Smritikosh 502K vs without Smritikosh 3.11M — 83.9% fewer. Source: decoded assistant usage entries."
        />
        <MetricChart
          title="Recorded cost by approach"
          values={[0.67360625, 2.45107]}
          unit="cost units"
          caption="Smritikosh 0.674 vs without Smritikosh 2.45 — 72.5% less. Currency was not recorded."
        />
      </Grid>

      <H2>Token and cost composition</H2>
      <Table
        headers={["Usage component", "Smritikosh", "Without Smritikosh", "Smritikosh reduction"]}
        rows={[
          ["Input tokens", "44", "90", "51.1% fewer · 2.05×"],
          ["Output tokens", "7.34K (7,336)", "12.3K (12,315)", "40.4% fewer · 1.68×"],
          ["Cache-read tokens", "452.6K (452,635)", "3.00M (2,999,565)", "84.9% fewer · 6.63×"],
          ["Cache-write tokens", "42.2K (42,187)", "102.9K (102,874)", "59.0% fewer · 2.44×"],
          ["Total tokens", "502K (502,202)", "3.11M (3,114,844)", "83.9% fewer · 6.20×"],
          ["Output cost", "0.183", "0.308", "40.4% less · 1.68×"],
          ["Cache-read cost", "0.226", "1.50", "84.9% less · 6.63×"],
          ["Cache-write cost", "0.264", "0.643", "59.0% less · 2.44×"],
          ["Grand cost", "0.674", "2.45", "72.5% less · 3.64×"],
        ]}
        columnAlign={["left", "right", "right", "right"]}
        striped
      />
      <Text size="small" tone="tertiary">
        Cache reads dominate the difference. Reasoning tokens were separately reported as 659 for
        Smritikosh and 2.17K (2,167) without Smritikosh and are not added again to the usage total.
      </Text>

      <H2>Tool calls and reads</H2>
      <Grid columns={2} gap={16}>
        <Card collapsible defaultOpen>
          <CardHeader trailing={<Pill size="sm">20 calls · 53.5% fewer</Pill>}>Smritikosh — indexed exploration</CardHeader>
          <CardBody>
            <Stack gap={10}>
              <Text>
                All 20 outer calls used <Code>bash</Code> to invoke Smritikosh. Nested operations:
                1 tools, 1 info, 9 search, 9 text, and 17 chunks (37 operations total).
              </Text>
              <Text size="small" tone="secondary">
                17 read-like chunk calls across 13 unique repository files. Repeats:
                statement_processor.py ×3; statement_eligibility.py ×2;
                statement_summary_event_generator.py ×2.
              </Text>
              <Divider />
              <Stack gap={5}>
                {session1Files.map((path) => (
                  <div key={path}><Text size="small"><Code>{path}</Code></Text></div>
                ))}
              </Stack>
            </Stack>
          </CardBody>
        </Card>

        <Card collapsible defaultOpen>
          <CardHeader trailing={<Pill size="sm">43 calls</Pill>}>Without Smritikosh — direct exploration</CardHeader>
          <CardBody>
            <Stack gap={10}>
              <Text>
                All 43 outer calls used <Code>bash</Code>. There were 25 explicit cat/sed reads across
                22 unique files, plus broad searches and repository inventories.
              </Text>
              <Text size="small" tone="secondary">
                One GitHub-root search returned unrelated repository data. Evidence also included draft
                memory, AI reference, runbook, and repository-local skill files.
              </Text>
              <Divider />
              <Table
                headers={["Repository", "Directly read material"]}
                rows={session2FileGroups}
                framed={false}
              />
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>Result relevance and evidence</H2>
      <Table
        headers={["Dimension", "Smritikosh", "Without Smritikosh"]}
        rows={[
          ["Impacted-service set", "Exact expected four", "Expected four + prc-ledger-svc"],
          ["Likely root cause", "Zero balance + no ledger activity suppresses PDF and notification", "Same core gates, with broader alternatives"],
          ["Test evidence", "Useful, but zero-balance handler test remained unverified", "Found definitive zero-balance publish_flag=false test"],
          ["Notification analysis", "Relevant handler/routing evidence", "Deeper eligibility, blocked-status, S3/template gates"],
          ["Account-service treatment", "Included, correctly bounded as cycle-close/delinquency behavior", "Included as account/cycle source data"],
          ["Ledger treatment", "Not promoted to impacted", "Promoted to ownership, then called unlikely for a missing statement"],
          ["Directness", "Focused, transparent about missing proof", "More complete but more speculative and internally inconsistent"],
          ["Noise", "Low", "Higher: global search plus secondary reference material"],
        ]}
        rowTone={["success", undefined, "warning", undefined, undefined, "danger", "success", "warning"]}
        striped
      />

      <Grid columns={2} gap={16}>
        <Stack gap={8} style={{ padding: 14, background: theme.fill.tertiary }}>
          <H3>Smritikosh efficiency per correct service</H3>
          <Text>33.4 seconds · 5 calls · 125.6K tokens · 0.168 cost units</Text>
        </Stack>
        <Stack gap={8} style={{ padding: 14, background: theme.fill.tertiary }}>
          <H3>Without Smritikosh efficiency per correct service</H3>
          <Text>129.7 seconds · 10.75 calls · 778.7K tokens · 0.613 cost units</Text>
        </Stack>
      </Grid>

      <Callout tone="info" title="Recommendation">
        Prefer Smritikosh's scoped retrieval and four-service classification. Borrow the direct
        zero-balance test citation and notification-gate evidence from the run without Smritikosh,
        but keep <Code>prc-ledger-svc</Code> as supporting context—not an impacted service—unless the
        impact definition explicitly includes upstream data providers.
      </Callout>

      <Text size="small" tone="tertiary">
        Method: decoded each HTML's embedded session JSON. Time ends at the last entry because no explicit
        end event exists. Exact filesystem bytes, full-file line counts, per-command durations, and cost
        currency were not reported and were not estimated.
      </Text>
    </Stack>
  );
}
