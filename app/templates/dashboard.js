"use strict";

const field = (id) => document.getElementById(id);
const tenant = field("tenant");
const status = field("status");
const panels = {
  subscription: "/subscription",
  usage: "/usage/summary",
  invoices: "/invoices?limit=20",
  audit: "/audit?limit=20",
};
let bearer = "";
let generation = 0;

async function read(path) {
  const response = await fetch(path, {
    headers: { Authorization: `Bearer ${bearer}` },
    cache: "no-store",
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.message || `HTTP ${response.status}`);
  return body;
}

function clear() {
  for (const id of Object.keys(panels)) field(id).textContent = "";
}

async function loadTenant() {
  const current = ++generation;
  clear();
  if (!tenant.value) return;
  status.textContent = "正在查询企业数据…";
  const prefix = `/v1/tenants/${encodeURIComponent(tenant.value)}`;
  await Promise.all(Object.entries(panels).map(async ([id, path]) => {
    try {
      const data = await read(prefix + path);
      if (current === generation) field(id).textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      if (current === generation) field(id).textContent = error.message;
    }
  }));
  if (current === generation) status.textContent = "";
}

field("credentials").addEventListener("submit", async (event) => {
  event.preventDefault();
  const current = ++generation;
  bearer = field("token").value.trim();
  field("token").value = "";
  tenant.replaceChildren();
  tenant.disabled = true;
  clear();
  try {
    const data = await read("/v1/tenants?limit=100");
    if (current !== generation) return;
    for (const item of data.items) tenant.add(new Option(item.name, item.id));
    tenant.disabled = !data.items.length;
    if (data.items.length) await loadTenant();
    else status.textContent = "当前账号没有企业。";
  } catch (error) {
    if (current === generation) status.textContent = error.message;
  }
});

tenant.addEventListener("change", loadTenant);
