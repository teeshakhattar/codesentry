async function runReview() {

    const repoUrl = document.getElementById("repoUrl").value.trim();

    if (!repoUrl) {
        alert("Please enter a repository URL.");
        return;
    }

    try {

        console.log("Step 1");

        const data = await reviewRepository(repoUrl);

        console.log("Step 2");

        console.log(data);

        renderDashboard(data);

    } catch (error) {

        console.error("ERROR:", error);

        alert(error.message);

    }

}

function renderDashboard(data){

    console.log("Rendering Dashboard");

    document.getElementById("repositoryName").innerText =
        data.repository;

    document.getElementById("riskScore").innerText =
        data.repository_risk_score;

    document.getElementById("riskBand").innerText =
        data.repository_risk_band;

    document.getElementById("filesReviewed").innerText =
        data.files_reviewed;
}