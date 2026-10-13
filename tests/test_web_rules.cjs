"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { evaluateTask } = require("../web/app.js");

function payload(overrides = {}) {
  return {
    task_id: "DEMO-001", target_identifier: "SAMPLE-A01",
    primary_metric: 10, secondary_metric: 5,
    status_descriptor: "NOMINAL", is_critical_flag: false, ...overrides
  };
}

test("normal inputs produce no rule alerts", () => {
  const result = evaluateTask(payload());
  assert.equal(result.overall_urgency, "ROUTINE");
  assert.equal(result.total_alerts, 0);
  assert.equal(result.robot_executed, false);
  assert.equal(result.validated_opentrons_protocol, false);
});

test("individual metric thresholds are strict greater-than comparisons", () => {
  assert.equal(evaluateTask(payload({ primary_metric: 25, secondary_metric: 12 })).total_alerts, 0);
  assert.equal(evaluateTask(payload({ primary_metric: 25.001 })).overall_urgency, "ELEVATED_RISK");
  assert.equal(evaluateTask(payload({ secondary_metric: 12.001 })).overall_urgency, "ELEVATED_RISK");
});

test("critical flag escalates risk regardless of other values", () => {
  const result = evaluateTask(payload({ is_critical_flag: true }));
  assert.equal(result.overall_urgency, "CRITICAL_STAT_PANIC");
  assert.equal(result.total_alerts, 1);
});

test("descriptor keywords match the Python worker rule", () => {
  assert.equal(evaluateTask(payload({ status_descriptor: "nominal" })).total_alerts, 0);
  assert.equal(evaluateTask(payload({ status_descriptor: "discordant-anomaly" })).total_alerts, 1);
  assert.equal(evaluateTask(payload({ status_descriptor: "FAIL" })).total_alerts, 1);
});

test("invalid metrics and identifiers are not interpreted as valid evidence", () => {
  assert.throws(() => evaluateTask(payload({ primary_metric: Infinity })), RangeError);
  assert.throws(() => evaluateTask(payload({ secondary_metric: NaN })), RangeError);
  assert.throws(() => evaluateTask(payload({ target_identifier: "" })), RangeError);
  assert.throws(() => evaluateTask(payload({ primary_metric: "12" })), RangeError);
});
