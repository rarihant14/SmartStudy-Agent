const jokes = [
  "🤖 Reading syllabus like topper mode ON 😄",
  "📚 Don’t worry, I won’t schedule 12 hours/day 😂",
  "😎 Making plan… backlog is scared now!",
  "☕ Adding revision so you don’t panic on last day!",
  "✅ Generating plan… please don’t close tab 👀"
];

let jokeInterval = null;

function showThinking(show) {
  const box = document.getElementById("thinkingBox");
  if (show) box.classList.remove("hidden");
  else box.classList.add("hidden");
}

function startJokes() {
  const line = document.getElementById("jokeLine");
  let i = 0;
  line.innerText = jokes[i];

  jokeInterval = setInterval(() => {
    i = (i + 1) % jokes.length;
    line.innerText = jokes[i];
  }, 1700);
}

function stopJokes() {
  if (jokeInterval) clearInterval(jokeInterval);
  jokeInterval = null;
}

/* ---------------- UPLOAD PDF ---------------- */

async function uploadPDF(){
  const fileInput = document.getElementById("pdfFile");
  const status = document.getElementById("pdfStatus");

  if (!fileInput.files.length){
    alert("Please select a PDF file!");
    return;
  }

  const formData = new FormData();
  formData.append("pdf", fileInput.files[0]);

  status.innerText = "Uploading & indexing syllabus...";

  const res = await fetch("/upload-syllabus", {
    method: "POST",
    body: formData
  });

  const data = await res.json();

  if(data.message){
    status.innerText = `✅ Uploaded: ${data.filename} | Indexed chunks: ${data.chunks_indexed}`;
  } else {
    status.innerText = "❌ Upload failed!";
  }
}

/* ---------------- PLAN RENDER ---------------- */

function renderPlan(plan) {
  const output = document.getElementById("planOutput");
  output.innerHTML = "";

  if (!plan || plan.length === 0) {
    output.innerHTML = `<div class="meta">No plan yet. Generate one ✅</div>`;
    return;
  }

  plan.forEach(item => {
    output.innerHTML += `
      <div class="planItem">
        <div class="planLeft">
          <b>${item.date} • ${item.subject}</b>
          <div class="meta">${item.topic}</div>
          <div class="meta">⏳ ${item.hours} hrs</div>
          ${item.status === "done" ? `<span class="doneBadge">✅ Done</span>` : ""}
        </div>

        <div>
          ${item.id ? `
            <button class="smallBtn" onclick="markDone(${item.id})">Done ✅</button>
            <button class="deleteBtn" onclick="deleteTask(${item.id})">Delete 🗑️</button>
          ` : ""}
        </div>
      </div>
    `;
  });
}

async function loadSavedPlans() {
  const res = await fetch("/plans");
  const data = await res.json();
  renderPlan(data);
}

async function markDone(planId) {
  await fetch(`/mark-done/${planId}`, { method: "POST" });
  await loadSavedPlans();
}

/* ✅ DELETE SINGLE TASK */
async function deleteTask(planId){
  const ok = confirm("Are you sure you want to delete this task? 🗑️");
  if(!ok) return;

  await fetch(`/delete-plan/${planId}`, { method: "POST" });
  await loadSavedPlans();
}

/* ✅ DELETE ALL TASKS */
async function deleteAllPlans(){
  const ok = confirm("⚠ Are you sure you want to DELETE ALL plans?");
  if(!ok) return;

  await fetch(`/delete-all-plans`, { method: "POST" });
  await loadSavedPlans();
}

/* ---------------- GENERATE PLAN ---------------- */

async function generatePlan() {
  const subjectsRaw = document.getElementById("subjects").value.trim();
  const exam_date = document.getElementById("exam_date").value;
  const hours_per_day = document.getElementById("hours").value;

  if (!subjectsRaw || !exam_date || !hours_per_day) {
    alert("⚠ Please fill all inputs!");
    return;
  }

  const subjects = subjectsRaw.split(",").map(s => s.trim()).filter(Boolean);

  try {
    showThinking(true);
    startJokes();

    const res = await fetch("/generate-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subjects, exam_date, hours_per_day })
    });

    const data = await res.json();

    stopJokes();
    showThinking(false);

    if (!data.plan) {
      alert("❌ Plan not generated. Check backend logs.");
      return;
    }

    await loadSavedPlans();

  } catch (err) {
    stopJokes();
    showThinking(false);
    alert("❌ Something went wrong! Check Flask logs.");
    console.error(err);
  }
}

/* ---------------- NEXT TOPIC ---------------- */

async function getNextTopic(){
  const box = document.getElementById("nextTopicBox");
  box.innerHTML = "🤖 Finding your next best topic...";

  const res = await fetch("/what-should-i-study");
  const data = await res.json();

  if(!data.task){
    box.innerHTML = `<div class="meta">${data.message}</div>`;
    return;
  }

  const t = data.task;

  box.innerHTML = `
    <div class="planItem">
      <div class="planLeft">
        <b>${t.subject}</b>
        <div class="meta">${t.topic}</div>
        <div class="meta">📅 ${t.date} • ⏳ ${t.hours} hrs</div>
      </div>
      <div>
        <button class="smallBtn" onclick="markDone(${t.id})">Mark Done ✅</button>
        <button class="deleteBtn" onclick="deleteTask(${t.id})">Delete 🗑️</button>
      </div>
    </div>
  `;
}

/* ---------------- DAILY GOALS ---------------- */

async function loadDailyGoals(){
  const box = document.getElementById("dailyGoalsBox");
  box.innerHTML = "🤖 Selecting today’s 3 mandatory topics...";

  const res = await fetch("/daily-goals");
  const data = await res.json();

  if(!data.goals || data.goals.length === 0){
    box.innerHTML = `<div class="meta">✅ No pending tasks left! Revise or do mock test 😄</div>`;
    return;
  }

  let html = `<div class="meta"><b>${data.message}</b> (Date: ${data.today})</div><br/>`;

  data.goals.forEach((t, idx) => {
    html += `
      <div class="planItem">
        <div class="planLeft">
          <b>Goal ${idx + 1}: ${t.subject}</b>
          <div class="meta">${t.topic}</div>
          <div class="meta">📅 ${t.date} • ⏳ ${t.hours} hrs</div>
        </div>
        <div>
          <button class="smallBtn" onclick="markDone(${t.id})">Done ✅</button>
          <button class="deleteBtn" onclick="deleteTask(${t.id})">Delete 🗑️</button>
        </div>
      </div>
    `;
  });

  box.innerHTML = html;
}

/* ---------------- CHATBOT ---------------- */

function addMessage(text, type){
  const box = document.getElementById("chatBox");
  const div = document.createElement("div");
  div.className = "msg " + (type === "user" ? "userMsg" : "aiMsg");
  div.innerText = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

async function sendChat(){
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if(!message) return;

  addMessage(message, "user");
  input.value = "";

  addMessage("🤖 Thinking...", "ai");

  const res = await fetch("/chat", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({message})
  });

  const data = await res.json();

  // remove last thinking msg
  const box = document.getElementById("chatBox");
  box.removeChild(box.lastChild);

  addMessage(data.reply, "ai");
}

window.onload = loadSavedPlans;
