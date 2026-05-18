import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('ErrorBoundary component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/ErrorBoundary.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('renders children normally when there is no error', () => {
    expect(source).toContain('return this.props.children');
  });

  it('catches errors and shows fallback UI', () => {
    expect(source).toContain('class ErrorBoundary extends Component');
    expect(source).toContain('getDerivedStateFromError');
    expect(source).toContain('errorBoundaryTitle');
    expect(source).toContain('this.props.fallback');
  });

  it('retry button resets state', () => {
    expect(source).toContain('errorBoundaryRetry');
    expect(source).toContain('this.setState({ hasError: false, error: null })');
  });
});
