import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie
} from 'recharts';
import { ScoreGauge } from '../components/ScoreGauge';
import { 
  Shield, 
  Search, 
  Eye, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Clock,
  Wrench
} from 'lucide-react';
import './Project.css';

// Types
interface SecurityFinding {
  rule_id: string;
  severity: string;
  message: string;
  file_path: string;
  line_start: number;
  line_end: number;
  code_snippet: string;
  fix_suggestion: string | null;
  auto_fixed: boolean;
  fix_verified: boolean;
}

interface SecurityReport {
  total_findings: number;
  auto_fixed: number;
  fix_verified: number;
  suggestions_only: number;
  findings: SecurityFinding[];
  by_severity: Record<string, { found: number; auto_fixed: number }>;
  scan_time: number;
}

interface SEOScores {
  performance: number;
  accessibility: number;
  best_practices: number;
  seo: number;
}

interface SEOReport {
  scores: SEOScores;
  issues: Array<{
    category: string;
    title: string;
    description: string;
    score: number | null;
    impact: string;
  }>;
  meta_tags: Record<string, string>;
  sitemap_generated: boolean;
  robots_generated: boolean;
  scan_time: number;
}

interface AccessibilityIssue {
  id: string;
  impact: string;
  description: string;
  help: string;
  help_url: string;
  wcag_tags: string[];
  nodes: Array<{ html?: string; file?: string; line?: number }>;
  fix_suggestion: string;
}

interface AccessibilityReport {
  total_violations: number;
  passes: number;
  incomplete: number;
  violations: AccessibilityIssue[];
  by_impact: Record<string, number>;
  wcag_compliance: Record<string, boolean>;
  scan_time: number;
}

interface QualityReports {
  security: SecurityReport | null;
  seo: SEOReport | null;
  accessibility: AccessibilityReport | null;
}

// Severity badge component
const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const colorMap: Record<string, string> = {
    critical: 'var(--severity-critical)',
    high: 'var(--severity-high)',
    serious: 'var(--severity-high)',
    medium: 'var(--severity-medium)',
    moderate: 'var(--severity-medium)',
    low: 'var(--severity-low)',
    minor: 'var(--severity-low)',
  };

  return (
    <span 
      className="severity-badge"
      style={{ 
        backgroundColor: colorMap[severity.toLowerCase()] || 'var(--text-muted)',
      }}
    >
      {severity.toUpperCase()}
    </span>
  );
};

// WCAG Tag component
const WCAGTag: React.FC<{ tag: string }> = ({ tag }) => {
  return (
    <span className="wcag-tag">
      {tag}
    </span>
  );
};

// Collapsible section component
const CollapsibleSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
}> = ({ title, icon, children, defaultOpen = false, badge }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="collapsible-section">
      <button 
        className="collapsible-header"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="collapsible-title">
          {icon}
          <span>{title}</span>
          {badge}
        </div>
        {isOpen ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
      </button>
      {isOpen && (
        <div className="collapsible-content">
          {children}
        </div>
      )}
    </div>
  );
};

// Security Findings Section
const SecuritySection: React.FC<{ report: SecurityReport }> = ({ report }) => {
  const severityData = Object.entries(report.by_severity).map(([severity, data]) => ({
    name: severity.charAt(0).toUpperCase() + severity.slice(1),
    found: data.found,
    fixed: data.auto_fixed,
    severity,
  }));

  const severityColors: Record<string, string> = {
    critical: '#dc2626',
    high: '#ea580c',
    medium: '#f59e0b',
    low: '#84cc16',
  };

  return (
    <div className="report-section">
      <div className="report-header">
        <Shield className="report-icon" />
        <h3>Security Scan</h3>
        <span className="scan-time">
          <Clock size={14} /> {report.scan_time.toFixed(1)}s
        </span>
      </div>

      <div className="report-stats">
        <div className="stat-card">
          <span className="stat-value">{report.total_findings}</span>
          <span className="stat-label">Total Findings</span>
        </div>
        <div className="stat-card success">
          <span className="stat-value">{report.auto_fixed}</span>
          <span className="stat-label">Auto-Fixed</span>
        </div>
        <div className="stat-card success">
          <span className="stat-value">{report.fix_verified}</span>
          <span className="stat-label">Verified</span>
        </div>
        <div className="stat-card warning">
          <span className="stat-value">{report.suggestions_only}</span>
          <span className="stat-label">Manual Review</span>
        </div>
      </div>

      {/* Severity Chart */}
      <div className="chart-container">
        <h4>Findings by Severity</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={severityData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
            <XAxis type="number" stroke="var(--text-secondary)" />
            <YAxis type="category" dataKey="name" stroke="var(--text-secondary)" width={80} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'var(--background-elevated)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--radius-md)',
              }}
            />
            <Bar dataKey="found" name="Found" stackId="a">
              {severityData.map((entry) => (
                <Cell key={entry.severity} fill={severityColors[entry.severity]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Findings List */}
      <CollapsibleSection 
        title="Vulnerability Details" 
        icon={<AlertTriangle size={16} />}
        badge={<span className="count-badge">{report.findings.length}</span>}
      >
        <div className="findings-list">
          {report.findings.map((finding, index) => (
            <div key={index} className="finding-item">
              <div className="finding-header">
                <SeverityBadge severity={finding.severity} />
                <span className="finding-rule">{finding.rule_id}</span>
                {finding.auto_fixed && (
                  <span className="auto-fix-badge">
                    <Wrench size={12} />
                    {finding.fix_verified ? 'Fixed & Verified' : 'Auto-Fixed'}
                  </span>
                )}
              </div>
              <p className="finding-message">{finding.message}</p>
              <div className="finding-location">
                <code>{finding.file_path}:{finding.line_start}</code>
              </div>
              {finding.code_snippet && (
                <pre className="finding-code">{finding.code_snippet}</pre>
              )}
              {finding.fix_suggestion && (
                <div className="fix-suggestion">
                  <strong>Suggestion:</strong> {finding.fix_suggestion}
                </div>
              )}
            </div>
          ))}
        </div>
      </CollapsibleSection>
    </div>
  );
};

// SEO/Lighthouse Section
const SEOSection: React.FC<{ report: SEOReport }> = ({ report }) => {
  return (
    <div className="report-section">
      <div className="report-header">
        <Search className="report-icon" />
        <h3>SEO & Performance</h3>
        <span className="scan-time">
          <Clock size={14} /> {report.scan_time.toFixed(1)}s
        </span>
      </div>

      {/* Lighthouse Scores */}
      <div className="lighthouse-scores">
        <ScoreGauge score={report.scores.performance} label="Performance" size="md" />
        <ScoreGauge score={report.scores.accessibility} label="Accessibility" size="md" />
        <ScoreGauge score={report.scores.best_practices} label="Best Practices" size="md" />
        <ScoreGauge score={report.scores.seo} label="SEO" size="md" />
      </div>

      {/* Generated Assets */}
      <div className="generated-assets">
        <h4>Generated Assets</h4>
        <div className="asset-list">
          <div className={`asset-item ${report.sitemap_generated ? 'success' : 'pending'}`}>
            {report.sitemap_generated ? <CheckCircle size={16} /> : <XCircle size={16} />}
            <span>sitemap.xml</span>
          </div>
          <div className={`asset-item ${report.robots_generated ? 'success' : 'pending'}`}>
            {report.robots_generated ? <CheckCircle size={16} /> : <XCircle size={16} />}
            <span>robots.txt</span>
          </div>
          <div className={`asset-item ${Object.keys(report.meta_tags).length > 0 ? 'success' : 'pending'}`}>
            {Object.keys(report.meta_tags).length > 0 ? <CheckCircle size={16} /> : <XCircle size={16} />}
            <span>Meta Tags ({Object.keys(report.meta_tags).length})</span>
          </div>
        </div>
      </div>

      {/* SEO Issues */}
      {report.issues.length > 0 && (
        <CollapsibleSection
          title="SEO Issues"
          icon={<AlertTriangle size={16} />}
          badge={<span className="count-badge">{report.issues.length}</span>}
        >
          <div className="findings-list">
            {report.issues.map((issue, index) => (
              <div key={index} className="finding-item">
                <div className="finding-header">
                  <span className="finding-category">{issue.category}</span>
                  <SeverityBadge severity={issue.impact} />
                </div>
                <p className="finding-title">{issue.title}</p>
                <p className="finding-message">{issue.description}</p>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
};

// Accessibility Section
const AccessibilitySection: React.FC<{ report: AccessibilityReport }> = ({ report }) => {
  const impactData = Object.entries(report.by_impact).map(([impact, count]) => ({
    name: impact.charAt(0).toUpperCase() + impact.slice(1),
    value: count,
    impact,
  }));

  const impactColors: Record<string, string> = {
    critical: '#dc2626',
    serious: '#ea580c',
    moderate: '#f59e0b',
    minor: '#84cc16',
  };

  const wcagStatus = Object.entries(report.wcag_compliance);

  return (
    <div className="report-section">
      <div className="report-header">
        <Eye className="report-icon" />
        <h3>Accessibility (WCAG 2.1 AA)</h3>
        <span className="scan-time">
          <Clock size={14} /> {report.scan_time.toFixed(1)}s
        </span>
      </div>

      <div className="report-stats">
        <div className="stat-card error">
          <span className="stat-value">{report.total_violations}</span>
          <span className="stat-label">Violations</span>
        </div>
        <div className="stat-card success">
          <span className="stat-value">{report.passes}</span>
          <span className="stat-label">Passes</span>
        </div>
        <div className="stat-card warning">
          <span className="stat-value">{report.incomplete}</span>
          <span className="stat-label">Incomplete</span>
        </div>
      </div>

      {/* WCAG Compliance Status */}
      <div className="wcag-compliance">
        <h4>WCAG Compliance</h4>
        <div className="wcag-status-list">
          {wcagStatus.map(([level, compliant]) => (
            <div key={level} className={`wcag-status ${compliant ? 'compliant' : 'non-compliant'}`}>
              {compliant ? <CheckCircle size={16} /> : <XCircle size={16} />}
              <span>{level.toUpperCase()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Impact Distribution */}
      {impactData.some(d => d.value > 0) && (
        <div className="chart-container">
          <h4>Violations by Impact</h4>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={impactData.filter(d => d.value > 0)}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {impactData.map((entry) => (
                  <Cell key={entry.impact} fill={impactColors[entry.impact]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--background-elevated)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: 'var(--radius-md)',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Violations List */}
      {report.violations.length > 0 && (
        <CollapsibleSection
          title="Accessibility Violations"
          icon={<AlertTriangle size={16} />}
          badge={<span className="count-badge">{report.violations.length}</span>}
        >
          <div className="findings-list">
            {report.violations.map((violation, index) => (
              <div key={index} className="finding-item">
                <div className="finding-header">
                  <SeverityBadge severity={violation.impact} />
                  <span className="finding-rule">{violation.id}</span>
                  <a 
                    href={violation.help_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="help-link"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>
                <p className="finding-message">{violation.description}</p>
                <p className="finding-help">{violation.help}</p>
                <div className="wcag-tags">
                  {violation.wcag_tags.slice(0, 4).map((tag, i) => (
                    <WCAGTag key={i} tag={tag} />
                  ))}
                </div>
                {violation.fix_suggestion && (
                  <div className="fix-suggestion">
                    <strong>Fix:</strong> {violation.fix_suggestion}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
};

// Main Project Page
const Project: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [qualityReports, setQualityReports] = useState<QualityReports>({
    security: null,
    seo: null,
    accessibility: null,
  });
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'quality' | 'code'>('quality');

  useEffect(() => {
    // Simulated data fetch - replace with actual API call
    const fetchReports = async () => {
      setLoading(true);
      try {
        // Mock data for demonstration
        const mockData: QualityReports = {
          security: {
            total_findings: 12,
            auto_fixed: 5,
            fix_verified: 5,
            suggestions_only: 7,
            findings: [
              {
                rule_id: 'javascript.security.hardcoded-secret',
                severity: 'critical',
                message: 'Hardcoded API key detected',
                file_path: 'src/config/api.ts',
                line_start: 15,
                line_end: 15,
                code_snippet: "const API_KEY = 'sk-123456789abcdef';",
                fix_suggestion: 'Move to environment variable',
                auto_fixed: true,
                fix_verified: true,
              },
              {
                rule_id: 'react.security.missing-noopener',
                severity: 'high',
                message: 'Missing rel="noopener noreferrer" on target="_blank" link',
                file_path: 'src/components/Footer.tsx',
                line_start: 42,
                line_end: 42,
                code_snippet: '<a href="https://example.com" target="_blank">',
                fix_suggestion: 'Add rel="noopener noreferrer" attribute',
                auto_fixed: true,
                fix_verified: true,
              },
            ],
            by_severity: {
              critical: { found: 1, auto_fixed: 1 },
              high: { found: 3, auto_fixed: 3 },
              medium: { found: 5, auto_fixed: 1 },
              low: { found: 3, auto_fixed: 0 },
            },
            scan_time: 12.5,
          },
          seo: {
            scores: {
              performance: 92,
              accessibility: 88,
              best_practices: 95,
              seo: 90,
            },
            issues: [
              {
                category: 'Performance',
                title: 'Largest Contentful Paint',
                description: 'LCP is 2.8s, aim for under 2.5s',
                score: 0.7,
                impact: 'medium',
              },
            ],
            meta_tags: {
              title: 'My Project',
              description: 'A modern web application',
              viewport: 'width=device-width, initial-scale=1.0',
            },
            sitemap_generated: true,
            robots_generated: true,
            scan_time: 28.3,
          },
          accessibility: {
            total_violations: 4,
            passes: 45,
            incomplete: 2,
            violations: [
              {
                id: 'color-contrast',
                impact: 'serious',
                description: 'Elements must have sufficient color contrast',
                help: 'Ensure the contrast between foreground and background colors meets WCAG 2 AA contrast ratio thresholds',
                help_url: 'https://dequeuniversity.com/rules/axe/4.4/color-contrast',
                wcag_tags: ['wcag2aa', 'wcag143'],
                nodes: [{ html: '<span class="text-gray-400">Low contrast text</span>' }],
                fix_suggestion: 'Increase the contrast ratio to at least 4.5:1 for normal text',
              },
              {
                id: 'image-alt',
                impact: 'critical',
                description: 'Images must have alternate text',
                help: 'Ensure images have an alt attribute that describes the image',
                help_url: 'https://dequeuniversity.com/rules/axe/4.4/image-alt',
                wcag_tags: ['wcag2a', 'wcag111'],
                nodes: [{ html: '<img src="/hero.jpg">' }],
                fix_suggestion: 'Add descriptive alt text: alt="Description of the image content"',
              },
            ],
            by_impact: {
              critical: 1,
              serious: 2,
              moderate: 1,
              minor: 0,
            },
            wcag_compliance: {
              wcag2a: false,
              wcag2aa: false,
              wcag21a: true,
              wcag21aa: true,
            },
            scan_time: 8.7,
          },
        };
        
        setQualityReports(mockData);
      } catch (error) {
        console.error('Failed to fetch quality reports:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, [projectId]);

  if (loading) {
    return (
      <div className="project-loading">
        <div className="loading-spinner"></div>
        <p>Loading quality reports...</p>
      </div>
    );
  }

  return (
    <div className="project-page">
      <header className="project-header">
        <h1>Project: {projectId || 'Demo Project'}</h1>
        <nav className="project-tabs">
          <button 
            className={activeTab === 'overview' ? 'active' : ''} 
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button 
            className={activeTab === 'quality' ? 'active' : ''} 
            onClick={() => setActiveTab('quality')}
          >
            Quality Reports
          </button>
          <button 
            className={activeTab === 'code' ? 'active' : ''} 
            onClick={() => setActiveTab('code')}
          >
            Code
          </button>
        </nav>
      </header>

      <main className="project-content">
        {activeTab === 'quality' && (
          <div className="quality-reports">
            <h2>Quality & Compliance Reports</h2>
            <p className="section-description">
              Automated security scanning, SEO auditing, and accessibility compliance checks.
            </p>

            <div className="reports-grid">
              {qualityReports.security && (
                <SecuritySection report={qualityReports.security} />
              )}
              
              {qualityReports.seo && (
                <SEOSection report={qualityReports.seo} />
              )}
              
              {qualityReports.accessibility && (
                <AccessibilitySection report={qualityReports.accessibility} />
              )}
            </div>
          </div>
        )}

        {activeTab === 'overview' && (
          <div className="overview-content">
            <h2>Project Overview</h2>
            <p>Project overview content coming soon...</p>
          </div>
        )}

        {activeTab === 'code' && (
          <div className="code-content">
            <h2>Code Explorer</h2>
            <p>Code explorer content coming soon...</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default Project;
