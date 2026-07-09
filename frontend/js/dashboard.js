async function runReview() {
    const repoUrlInput = document.getElementById("repoUrl");
    const reviewModeInput = document.getElementById("reviewMode");

    const repoUrl = repoUrlInput
        ? repoUrlInput.value.trim()
        : "";

    const mode = reviewModeInput
        ? reviewModeInput.value
        : "full";

    if (!repoUrl) {
        alert("Please enter a repository URL.");
        return;
    }

    try {
        console.log("Starting repository review...");
        console.log("Review mode:", mode);

        setReviewLoadingState(true, mode);

        let data;

        if (mode === "incremental") {
            console.log("Calling incremental review API...");
            data = await reviewRepositoryIncremental(repoUrl);
        } else {
            console.log("Calling full repository review API...");
            data = await reviewRepository(repoUrl);
        }

        console.log("Review completed:", data);

        if (!data) {
            throw new Error("API returned no response data.");
        }

        if (data.success === false) {
            throw new Error(
                data.error || "Repository review failed."
            );
        }

        renderDashboard(data);

        // Refresh recent scan history without breaking dashboard
        try {
            await loadRecentScans();
        } catch (historyError) {
            console.warn(
                "Dashboard rendered, but scan history refresh failed:",
                historyError
            );
        }

    } catch (error) {
        console.error("REVIEW ERROR:", error);

        alert(
            error.message ||
            "Something went wrong while reviewing the repository."
        );

    } finally {
        setReviewLoadingState(false, mode);
    }
}


function setReviewLoadingState(isLoading, mode = "full") {
    const button = document.getElementById("runReviewBtn");

    if (!button) {
        return;
    }

    button.disabled = isLoading;

    if (isLoading) {
        button.textContent =
            mode === "incremental"
                ? "Reviewing changes..."
                : "Reviewing repository...";
    } else {
        button.textContent =
            mode === "incremental"
                ? "Review changes"
                : "Run review";
    }
}


function renderDashboard(data) {
    console.log("Rendering dashboard with:", data);

    const repositoryName =
        document.getElementById("repositoryName");

    const riskScore =
        document.getElementById("riskScore");

    const riskBand =
        document.getElementById("riskBand");

    const filesReviewed =
        document.getElementById("filesReviewed");

    if (repositoryName) {
        repositoryName.innerText =
            data.repository ?? "Unknown";
    }

    if (riskScore) {
        repositoryName;
        riskScore.innerText =
            data.repository_risk_score ?? "N/A";
    }

    if (riskBand) {
        riskBand.innerText =
            data.repository_risk_band ?? "Unknown";
    }

    if (filesReviewed) {
        filesReviewed.innerText =
            data.files_reviewed ?? 0;
    }

    updateReviewModeDisplay(data);
}


function updateReviewModeDisplay(data) {
    const mode =
        data.review_mode === "incremental"
            ? "Incremental Review"
            : "Full Repository Review";

    console.log("Rendered review mode:", mode);

    const modeElement =
        document.getElementById("reviewModeResult");

    if (modeElement) {
        modeElement.innerText = mode;
    }
}


async function loadRecentScans() {
    const container =
        document.getElementById("recentScans");

    if (!container) {
        console.log(
            "Recent scans container not found yet."
        );
        return;
    }

    try {
        container.innerHTML =
            "<p>Loading recent scans...</p>";

        const scans = await getScans();

        renderRecentScans(scans);

    } catch (error) {
        console.error(
            "Failed to load scan history:",
            error
        );

        container.innerHTML =
            "<p>Could not load scan history.</p>";
    }
}


function renderRecentScans(scans) {
    const container =
        document.getElementById("recentScans");

    if (!container) {
        return;
    }

    if (!Array.isArray(scans) || scans.length === 0) {
        container.innerHTML =
            "<p>No scans available yet.</p>";
        return;
    }

    const recentScans = scans.slice(0, 5);

    container.innerHTML = recentScans
        .map(scan => {
            const repository =
                scan.repository ?? "Unknown";

            const riskScore =
                scan.repository_risk_score ?? "N/A";

            const riskBand =
                scan.repository_risk_band ?? "Unknown";

            const filesReviewed =
                scan.files_reviewed ?? 0;

            const scannedAt = scan.scanned_at
                ? new Date(scan.scanned_at).toLocaleString()
                : "Unknown time";

            return `
                <div class="scan-history-card">
                    <div class="scan-history-main">
                        <h3>
                            ${escapeHtml(repository)}
                        </h3>

                        <p>
                            ${escapeHtml(scannedAt)}
                        </p>
                    </div>

                    <div class="scan-history-stats">
                        <span>
                            Risk Score:
                            <strong>
                                ${escapeHtml(riskScore)}
                            </strong>
                        </span>

                        <span>
                            Risk Band:
                            <strong>
                                ${escapeHtml(riskBand)}
                            </strong>
                        </span>

                        <span>
                            Files:
                            <strong>
                                ${escapeHtml(filesReviewed)}
                            </strong>
                        </span>
                    </div>
                </div>
            `;
        })
        .join("");
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


document.addEventListener(
    "DOMContentLoaded",
    loadRecentScans
);