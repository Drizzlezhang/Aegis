const paths = ['/market', '/analyze', '/history', '/status', '/memory', '/backtest'];

for (const path of paths) {
  try {
    const res = await fetch(`http://127.0.0.1:3003${path}`);
    const html = await res.text();
    const empty = html.includes('Watchlist</h2><ul class="space-y-1"></ul>');
    console.log(path, empty ? 'empty' : 'non-empty');
  } catch (error) {
    console.error(path, String(error));
    process.exitCode = 1;
  }
}
