const targets = [
  'http://127.0.0.1:3003/api/symbols',
  'http://127.0.0.1:8003/api/symbols',
];

for (const url of targets) {
  try {
    const res = await fetch(url);
    const data = await res.json();
    console.log(url, JSON.stringify(data[0] ?? null));
  } catch (error) {
    console.error(url, String(error));
    process.exitCode = 1;
  }
}
