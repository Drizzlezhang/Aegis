const targets = [
  ['symbols', 'http://127.0.0.1:3003/api/symbols'],
  ['status', 'http://127.0.0.1:3003/api/status'],
];

for (const [name, url] of targets) {
  try {
    const res = await fetch(url);
    const data = await res.json();
    const sample = name === 'symbols'
      ? { symbol: data?.[0]?.symbol, price: data?.[0]?.price }
      : { version: data?.system?.version, uptime: data?.system?.uptime };
    console.log(name, JSON.stringify(sample));
  } catch (error) {
    console.error(name, String(error));
    process.exitCode = 1;
  }
}
