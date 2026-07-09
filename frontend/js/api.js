const API_BASE = "http://127.0.0.1:8000";


async function reviewRepository(repoUrl) {

    console.log("Calling review API...");

    const response = await fetch(`${API_BASE}/review-repository`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            repo_url: repoUrl
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail ||
            data.error ||
            "Repository review failed."
        );
    }

    if (data.success === false) {
        throw new Error(
            data.error ||
            "Repository review failed."
        );
    }

    console.log("Review response:", data);

    return data;
}


async function getScans() {

    console.log("Fetching scan history...");

    const response = await fetch(`${API_BASE}/scans`);

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail ||
            data.error ||
            "Failed to load scan history."
        );
    }

    console.log("Scan history:", data);

    return data;
}