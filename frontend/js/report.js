function getSavedReportPayload(data) {
    return data?.report || data?.scan || data?.result || data;
}


function getSavedReviews(report) {
    return Array.isArray(report?.reviews) ? report.reviews : [];
}


function getReviewObject(reviewItem) {
    const review = reviewItem?.review;

    if (!review) {
        return {};
    }

    if (typeof review === "object") {
        return review;
    }

    if (typeof review === "string") {
        try {
            return JSON.parse(review);
        } catch {
            return {
                summary: review,
                findings: [],
                clean_code: [],
                best_practices: []
            };
        }
    }

    return {};
}


function getFindings(reviewItem) {
    const review = getReviewObject(reviewItem);

    return Array.isArray(review?.findings)
        ? review.findings
        : [];
}


function getFindingCount(reviewItem) {
    const scoringCounts =
        reviewItem?.scoring?.finding_counts;

    if (scoringCounts) {
        return (
            Number(scoringCounts.High || 0) +
            Number(scoringCounts.Medium || 0) +
            Number(scoringCounts.Low || 0)
        );
    }

    return getFindings(reviewItem).length;
}


function getSeverityCounts(reviews) {
    const counts = {
        High: 0,
        Medium: 0,
        Low: 0
    };

    reviews.forEach(reviewItem => {
        const scoringCounts =
            reviewItem?.scoring?.finding_counts;

        if (scoringCounts) {
            counts.High += Number(scoringCounts.High || 0);
            counts.Medium += Number(scoringCounts.Medium || 0);
            counts.Low += Number(scoringCounts.Low || 0);
            return;
        }

        getFindings(reviewItem).forEach(finding => {
            const severity =
                String(finding?.severity || "").toLowerCase();

            if (severity === "high") {
                counts.High++;
            } else if (severity === "medium") {
                counts.Medium++;
            } else if (severity === "low") {
                counts.Low++;
            }
        });
    });

    return counts;
}


function getCleanFilePath(reviewItem, index) {
    const rawPath =
        reviewItem?.file_path ||
        reviewItem?.filename ||
        reviewItem?.file ||
        reviewItem?.path ||
        `File ${index + 1}`;

    const normalized =
        String(rawPath).replaceAll("\\", "/");

    const flaskMarker = "/src/";

    if (normalized.includes(flaskMarker)) {
        return normalized.split(flaskMarker)[1];
    }

    const sampleMarker = "/sample_repositories/";

    if (normalized.includes(sampleMarker)) {
        const afterSample =
            normalized.split(sampleMarker)[1];

        const parts = afterSample.split("/");

        return parts.slice(1).join("/") || parts[0];
    }

    return normalized.split("/").slice(-3).join("/");
}


function getRiskClass(riskBand) {
    const band =
        String(riskBand || "").toLowerCase();

    if (band.includes("critical")) return "critical";
    if (band.includes("high")) return "high";
    if (band.includes("medium")) return "medium";
    if (band.includes("low")) return "low";

    return "unknown";
}


function getSeverityClass(severity) {
    const value =
        String(severity || "").toLowerCase();

    if (value === "high") return "high";
    if (value === "medium") return "medium";
    if (value === "low") return "low";

    return "unknown";
}


function formatSavedReportDate(value) {
    if (!value) {
        return "Not available";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString();
}


function escapeReportHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function hideDashboardForReport() {
    const idsToHide = [
        "emptyState",
        "overviewCards",
        "analyticsRow",
        "contentRow",
        "repositoriesView"
    ];

    idsToHide.forEach(id => {
        const element = document.getElementById(id);

        if (element) {
            element.style.display = "none";
            element.classList.remove("active");
        }
    });
}


function renderFindingCard(finding, findingIndex) {
    const severity =
        finding?.severity || "Unknown";

    const category =
        finding?.category || "General";

    const issue =
        finding?.issue ||
        finding?.message ||
        "No issue description available.";

    const line =
        finding?.line ??
        finding?.line_number ??
        "N/A";

    return `
        <div class="report-finding-card">

            <div class="report-finding-top">

                <div class="report-finding-title-group">
                    <span class="report-finding-number">
                        ISSUE ${findingIndex + 1}
                    </span>

                    <span class="report-category-badge">
                        ${escapeReportHtml(category)}
                    </span>
                </div>

                <span class="report-severity-badge ${getSeverityClass(severity)}">
                    ${escapeReportHtml(severity)}
                </span>

            </div>

            <p class="report-finding-text">
                ${escapeReportHtml(issue)}
            </p>

            <div class="report-finding-meta">
                Line ${escapeReportHtml(line)}
            </div>

        </div>
    `;
}


function renderSuggestionList(items, emptyMessage) {
    if (!Array.isArray(items) || !items.length) {
        return `
            <p class="report-empty-text">
                ${escapeReportHtml(emptyMessage)}
            </p>
        `;
    }

    return `
        <ul class="report-suggestion-list">
            ${items.map(item => `
                <li>
                    ${escapeReportHtml(item)}
                </li>
            `).join("")}
        </ul>
    `;
}


function renderFileReport(reviewItem, index) {
    const review =
        getReviewObject(reviewItem);

    const findings =
        getFindings(reviewItem);

    const filePath =
        getCleanFilePath(reviewItem, index);

    const summary =
        review?.summary ||
        "No summary available for this file.";

    const cleanCode =
        review?.clean_code || [];

    const bestPractices =
        review?.best_practices || [];

    const score =
        review?.score ??
        reviewItem?.scoring?.score ??
        "N/A";

    return `
        <article class="report-file-card">

            <div class="report-file-header">

                <div class="report-file-heading">

                    <span class="report-file-number">
                        FILE ${index + 1}
                    </span>

                    <h3 class="report-file-name">
                        ${escapeReportHtml(filePath)}
                    </h3>

                </div>

                <div class="report-file-header-right">

                    <span class="report-score-badge">
                        Score ${escapeReportHtml(score)}
                    </span>

                    <span class="report-issue-count">
                        ${findings.length}
                        ${findings.length === 1 ? "issue" : "issues"}
                    </span>

                </div>

            </div>


            <div class="report-file-summary">

                <span class="report-mini-label">
                    SUMMARY
                </span>

                <p>
                    ${escapeReportHtml(summary)}
                </p>

            </div>


            <div class="report-file-section">

                <div class="report-subsection-heading">
                    <h4>Findings</h4>

                    <span>
                        ${findings.length}
                    </span>
                </div>

                ${
                    findings.length
                        ? findings
                            .map((finding, findingIndex) =>
                                renderFindingCard(
                                    finding,
                                    findingIndex
                                )
                            )
                            .join("")
                        : `
                            <div class="report-no-findings">
                                No issues detected in this file.
                            </div>
                        `
                }

            </div>


            <div class="report-advice-grid">

                <div class="report-advice-card">

                    <span class="report-mini-label">
                        CLEAN CODE
                    </span>

                    ${renderSuggestionList(
                        cleanCode,
                        "No clean-code suggestions available."
                    )}

                </div>


                <div class="report-advice-card">

                    <span class="report-mini-label">
                        BEST PRACTICES
                    </span>

                    ${renderSuggestionList(
                        bestPractices,
                        "No best-practice suggestions available."
                    )}

                </div>

            </div>

        </article>
    `;
}


function renderSavedReport(data) {
    const report =
        getSavedReportPayload(data);

    const reviews =
        getSavedReviews(report);

    if (!report || !reviews.length) {
        showCodeSentryModal(
            "Report Error",
            "The saved scan was loaded, but its report data is incomplete."
        );
        return;
    }

    lastData = report;

    const reportView =
        document.getElementById("reportView");

    if (!reportView) {
        showCodeSentryModal(
            "Report View Missing",
            "The report container could not be found in the dashboard."
        );
        return;
    }

    hideDashboardForReport();

    const repositoryName =
        report.repository ||
        report.repository_name ||
        data.repository ||
        "Repository";

    const riskScore =
        report.repository_risk_score ??
        report.risk_score ??
        "N/A";

    const riskBand =
        report.repository_risk_band ||
        report.risk_band ||
        "Unknown";

    const filesReviewed =
        report.files_reviewed ??
        reviews.length;

    const scannedAt =
        report.scanned_at ||
        report.created_at ||
        report.timestamp ||
        data.scanned_at;

    const severityCounts =
        getSeverityCounts(reviews);

    const totalIssues =
        severityCounts.High +
        severityCounts.Medium +
        severityCounts.Low;

    reportView.style.display = "block";

    reportView.innerHTML = `
        <section class="saved-report-page">

            <div class="report-page-header">

                <div>
                    <p class="report-eyebrow">
                        SAVED SCAN REPORT
                    </p>

                    <h1 class="report-title">
                        ${escapeReportHtml(repositoryName)}
                    </h1>

                    <p class="report-subtitle">
                        Detailed AI-assisted code review results
                        from this repository scan.
                    </p>
                </div>

                <button
                    type="button"
                    class="report-back-button"
                    onclick="closeSavedReport()"
                >
                    ← Back to Scan History
                </button>

            </div>


            <div class="report-summary-grid">

                <article class="report-summary-card">
                    <span class="report-card-label">
                        Risk Score
                    </span>

                    <strong class="report-card-value">
                        ${escapeReportHtml(riskScore)}
                    </strong>
                </article>


                <article class="report-summary-card">
                    <span class="report-card-label">
                        Risk Band
                    </span>

                    <strong class="report-risk-badge ${getRiskClass(riskBand)}">
                        ${escapeReportHtml(riskBand)}
                    </strong>
                </article>


                <article class="report-summary-card">
                    <span class="report-card-label">
                        Files Reviewed
                    </span>

                    <strong class="report-card-value">
                        ${escapeReportHtml(filesReviewed)}
                    </strong>
                </article>


                <article class="report-summary-card">
                    <span class="report-card-label">
                        Total Findings
                    </span>

                    <strong class="report-card-value">
                        ${totalIssues}
                    </strong>
                </article>

            </div>


            <div class="report-severity-grid">

                <div class="report-severity-stat high">
                    <span>High</span>
                    <strong>${severityCounts.High}</strong>
                </div>

                <div class="report-severity-stat medium">
                    <span>Medium</span>
                    <strong>${severityCounts.Medium}</strong>
                </div>

                <div class="report-severity-stat low">
                    <span>Low</span>
                    <strong>${severityCounts.Low}</strong>
                </div>

            </div>


            <div class="report-meta-bar">

                <span>
                    <strong>Repository:</strong>
                    ${escapeReportHtml(repositoryName)}
                </span>

                <span>
                    <strong>Scanned:</strong>
                    ${escapeReportHtml(
                        formatSavedReportDate(scannedAt)
                    )}
                </span>

            </div>


            <div class="report-files-section">

                <div class="report-section-heading">

                    <div>
                        <p class="report-eyebrow">
                            FILE ANALYSIS
                        </p>

                        <h2>
                            Reviewed Files
                        </h2>
                    </div>

                    <span class="report-file-count">
                        ${reviews.length} files
                    </span>

                </div>


                <div class="report-file-list">

                    ${reviews
                        .map((reviewItem, index) =>
                            renderFileReport(
                                reviewItem,
                                index
                            )
                        )
                        .join("")}

                </div>

            </div>

        </section>
    `;

    const pageTitle =
        document.getElementById("pageTitle");

    if (pageTitle) {
        pageTitle.innerHTML = `
            ${escapeReportHtml(repositoryName)}
            <span class="status-pill done">
                <span class="pdot"></span>
                Saved report
            </span>
        `;
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


async function openScanReport(scanId) {
    console.log(
        "Opening saved report:",
        scanId
    );

    try {
        const response = await fetch(
            `${API_BASE}/scans/${encodeURIComponent(scanId)}`
        );

        if (!response.ok) {
            throw new Error(
                `Failed to load report: ${response.status}`
            );
        }

        const data =
            await response.json();

        console.log(
            "Saved report received:",
            data
        );

        renderSavedReport(data);

    } catch (error) {
        console.error(
            "Report loading error:",
            error
        );

        showCodeSentryModal(
            "Unable to Load Report",
            "CodeSentry could not retrieve this saved scan report."
        );
    }
}


function closeSavedReport() {
    const reportView =
        document.getElementById("reportView");

    if (reportView) {
        reportView.style.display = "none";
        reportView.innerHTML = "";
    }

    const repositoriesView =
        document.getElementById("repositoriesView");

    if (repositoriesView) {
        repositoriesView.style.display = "block";
    }

    const pageTitle =
        document.getElementById("pageTitle");

    if (pageTitle) {
        pageTitle.textContent =
            "Repository Scan History";
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}