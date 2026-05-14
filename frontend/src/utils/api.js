import axios from "axios";

const base = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: base });

export async function post(url, data) {
  const res = await client.post(url, data);
  return res.data;
}

export async function get(url) {
  const res = await client.get(url);
  return res.data;
}
