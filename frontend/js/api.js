const API_BASE = "http://127.0.0.1:8000";

async function reviewRepository(repoUrl) {

    console.log("Calling API...");

    const response = await fetch(`${API_BASE}/review-repository`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            repo_url: repoUrl
        })
    });

    console.log("Response received");
    console.log(response);

    const data = await response.json();

    console.log("JSON parsed");
    console.log(data);

    return data;
}