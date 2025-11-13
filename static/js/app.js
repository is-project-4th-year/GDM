// // app.js — 10-field interactive UI, calls /predict-form (AJAX)

// const form = document.getElementById("gdmForm");
// const btn = document.getElementById("predictBtn");
// const loader = document.getElementById("loader");
// const resultBox = document.getElementById("result");
// const labelEl = document.getElementById("label");
// const barFill = document.getElementById("barFill");
// const probPct = document.getElementById("probPct");
// const riskBand = document.getElementById("riskBand");
// const table = document.getElementById("valuesTable");

// // The 10 UI fields we send (backend expands to all 15):
// const UI_FIELDS = [
//   "Age","BMI","Sys BP","Dia BP","Family History","PCOS",
//   "Prediabetes","Sedentary Lifestyle","HDL","Hemoglobin"
// ];

// function toFloatOrNull(v) {
//   if (v === null || v === undefined) return null;
//   const s = String(v).trim();
//   if (!s) return null;
//   const n = Number(s);
//   return Number.isFinite(n) ? n : null;
// }

// function formToRow10() {
//   const row = {};
//   UI_FIELDS.forEach(f => {
//     const el = form.elements[f];
//     row[f] = el ? toFloatOrNull(el.value) : null;
//   });
//   return row;
// }

// function setLoading(on) { btn.disabled = on; loader.hidden = !on; }

// function setBadge(pred) {
//   labelEl.textContent = pred === 1 ? "GDM (Positive)" : "Non-GDM (Negative)";
//   labelEl.className = "badge " + (pred === 1 ? "badge-red" : "badge-green");
// }

// function setBar(p) {
//   const pct = Math.round(p * 100);
//   barFill.style.width = pct + "%";
//   barFill.className = "bar-fill " + (p >= 0.5 ? "risk" : "safe");
//   probPct.textContent = pct + "%";
// }

// function setRiskBand(text) { riskBand.textContent = text; }

// function fillTable(row) {
//   const rows = UI_FIELDS.map(f => `<tr><td>${f}</td><td>${row[f] ?? ""}</td></tr>`).join("");
//   table.innerHTML = "<tr><th>Feature</th><th>Value</th></tr>" + rows;
// }

// form.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   const row10 = formToRow10();

//   setLoading(true);
//   try {
//     const resp = await fetch("/predict-form", {
//       method: "POST",
//       body: new URLSearchParams(row10) // submit as form-encoded, backend reads request.form
//     });
//     const data = await resp.json();
//     if (!resp.ok) throw new Error(data.error || "Prediction failed");

//     setBadge(data.prediction);
//     setBar(data.probability);
//     setRiskBand(data.risk_band);
//     fillTable(data.values);

//     resultBox.hidden = false;
//     resultBox.scrollIntoView({ behavior: "smooth" });
//   } catch (err) {
//     alert("Prediction failed: " + err.message);
//   } finally {
//     setLoading(false);
//   }
// });

// Simulated login redirection
document.getElementById("loginForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  window.location.href = "input.html";
});

// Simulate form submission and redirect
document.getElementById("patientForm")?.addEventListener("submit", (e) => {
  e.preventDefault();
  window.location.href = "predict.html";
});

// Display random prediction result
if (document.getElementById("result")) {
  const outcome = Math.random() > 0.5 ? "High likelihood of Diabetes" : "Low likelihood of Diabetes";
  document.getElementById("result").textContent = outcome;
}

// Back button
function goBack() {
  window.location.href = "input.html";
}

// Chart display on dashboard
if (document.getElementById("predictionChart")) {
  const ctx = document.getElementById("predictionChart").getContext("2d");
  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["High Risk", "Low Risk"],
      datasets: [
        {
          label: "Predictions",
          data: [65, 35],
          backgroundColor: ["#1976d2", "#ffca28"],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
}
