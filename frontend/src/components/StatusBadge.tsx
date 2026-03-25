interface StatusBadgeProps {
  violations: number;
  scanType: string;
}

function isRemediateType(scanType: string): boolean {
  return scanType === "fix" || scanType === "remediate";
}

function isCheckType(scanType: string): boolean {
  return scanType === "scan" || scanType === "check";
}

export function StatusBadge({ violations, scanType }: StatusBadgeProps) {
  if (violations > 0) {
    return <span className="apme-badge failed">{"\u2717"} {violations} ISSUES</span>;
  }
  if (isRemediateType(scanType)) {
    return <span className="apme-badge passed">{"\u2713"} Remediate</span>;
  }
  if (isCheckType(scanType)) {
    return <span className="apme-badge passed">{"\u2713"} Check</span>;
  }
  return <span className="apme-badge passed">{"\u2713"} Check</span>;
}
