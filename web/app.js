/* Browser-only demonstration of the same generic thresholds as agents/workers.py.
 * No robot is controlled, no API is contacted, and no signed audit record is produced.
 */
(function (root) {
  "use strict";

  function evaluateTask(payload) {
    if (!payload || typeof payload !== "object") throw new TypeError("A task is required.");
    const primary = Number(payload.primary_metric);
    const secondary = Number(payload.secondary_metric);
    if (typeof payload.primary_metric !== "number" || typeof payload.secondary_metric !== "number" ||
        !Number.isFinite(primary) || !Number.isFinite(secondary)) {
      throw new RangeError("Both metrics must be finite numbers.");
    }
    const taskId = String(payload.task_id || "").trim();
    const target = String(payload.target_identifier || "").trim();
    const descriptor = String(payload.status_descriptor || "NOMINAL").trim();
    if (!taskId || !target || taskId.length > 128 || target.length > 128 || descriptor.length > 256) {
      throw new RangeError("Enter short, nonempty identifiers and a descriptor under 257 characters.");
    }
    const critical = payload.is_critical_flag === true;
    const alerts = [];
    if (primary > 25) {
      alerts.push({
        origin_worker: "InvariantQCWorker",
        urgency: "ELEVATED_RISK",
        summary: "Primary metric exceeds demonstration threshold (25)."
      });
    }
    if (critical || secondary > 12) {
      alerts.push({
        origin_worker: "SafetyEscalationWorker",
        urgency: critical ? "CRITICAL_STAT_PANIC" : "ELEVATED_RISK",
        summary: critical
          ? "Critical flag explicitly set by the user."
          : "Secondary metric exceeds demonstration threshold (12)."
      });
    }
    if (["DISCORDANT", "ANOMALY", "MUTANT", "VIOLATION", "FAIL", "REJECT"]
      .some(function (word) { return descriptor.toUpperCase().includes(word); })) {
      alerts.push({
        origin_worker: "ProtocolConformanceWorker",
        urgency: "ELEVATED_RISK",
        summary: "Descriptor matches a configured warning keyword (not protocol validation)."
      });
    }
    const hasCritical = alerts.some(function (a) { return a.urgency === "CRITICAL_STAT_PANIC"; });
    const urgency = hasCritical ? "CRITICAL_STAT_PANIC" : alerts.length ? "ELEVATED_RISK" : "ROUTINE";
    return {
      tool: "opentrons-liquid-handler-agent",
      evaluation_type: "client_side_rule_demo",
      robot_executed: false,
      validated_opentrons_protocol: false,
      task_id: taskId,
      target_identifier: target,
      input: {
        primary_metric: primary, secondary_metric: secondary,
        status_descriptor: descriptor, is_critical_flag: critical
      },
      overall_urgency: urgency,
      total_alerts: alerts.length,
      alerts: alerts,
      note: "Generic thresholds only. No hardware validation, pipette calibration, or HMAC audit."
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { evaluateTask: evaluateTask };
  }
  if (typeof document === "undefined") return;

  document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("audit-form");
    const output = document.getElementById("output");
    const status = document.getElementById("status");
    const count = document.getElementById("task-count");
    const alertCount = document.getElementById("alert-count");
    const exportButton = document.getElementById("export");
    const resetButton = document.getElementById("reset");
    let runs = 0;
    let lastResult = null;

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      try {
        const result = evaluateTask({
          task_id: document.getElementById("task_id").value,
          target_identifier: document.getElementById("target_id").value,
          primary_metric: Number(document.getElementById("primary_metric").value),
          secondary_metric: Number(document.getElementById("secondary_metric").value),
          status_descriptor: document.getElementById("status_descriptor").value,
          is_critical_flag: document.getElementById("is_critical").checked
        });
        lastResult = result;
        runs += 1;
        count.textContent = String(runs);
        alertCount.textContent = String(result.total_alerts);
        status.textContent = result.overall_urgency === "ROUTINE" ? "No rule alerts" :
          result.overall_urgency === "ELEVATED_RISK" ? "Rule warning" : "Critical flag";
        status.dataset.level = result.overall_urgency;
        output.textContent = JSON.stringify(result, null, 2);
        exportButton.disabled = false;
      } catch (error) {
        lastResult = null;
        exportButton.disabled = true;
        output.textContent = "Evaluation failed: " + error.message;
        status.textContent = "Invalid input";
        status.dataset.level = "INVALID";
      }
    });

    exportButton.addEventListener("click", function () {
      if (!lastResult) return;
      const blob = new Blob([JSON.stringify(lastResult, null, 2) + "\n"], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "opentrons-rule-evaluation.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });

    resetButton.addEventListener("click", function () {
      form.reset();
      lastResult = null;
      runs = 0;
      count.textContent = "0";
      alertCount.textContent = "0";
      status.textContent = "Not evaluated";
      status.dataset.level = "";
      output.textContent = "Submit the example task to view a rule evaluation.";
      exportButton.disabled = true;
    });
  });
})(typeof globalThis === "object" ? globalThis : this);
