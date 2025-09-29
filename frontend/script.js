let clipsData = [];
let selected = [];

function fetchClips() {
    let keyword = document.getElementById("keyword").value;
    fetch(`/fetch?keyword=${keyword}`)
        .then(res => res.json())
        .then(data => {
            clipsData = data.clips;
            selected = [];
            renderClips();
        });
}

function renderClips() {
    let container = document.getElementById("clips-container");
    container.innerHTML = "";
    clipsData.forEach((clip, idx) => {
        let div = document.createElement("div");
        div.className = "clip";
        div.innerHTML = `<video src="/temp_videos/${clip}" width="100%" controls></video>`;
        div.onclick = () => {
            if(selected.includes(idx)) selected = selected.filter(i=>i!==idx);
            else selected.push(idx);
            div.classList.toggle("selected");
        };
        container.appendChild(div);
    });
}

function generateVideo() {
    if(selected.length === 0) { alert("Select at least one clip"); return; }
    let layout = document.getElementById("layout").value;
    let script = document.getElementById("script").value;
    let font_size = document.getElementById("font_size").value;
    let font_family = document.getElementById("font_family").value;

    let form = new FormData();
    form.append("clips", selected.map(i=>clipsData[i]).join(","));
    form.append("order", selected.join(","));
    form.append("start_times", selected.map(()=>0).join(",")); // default start at 0
    form.append("end_times", selected.map(()=>10).join(","));  // default 10s duration
    form.append("layout", layout);
    form.append("script", script);
    form.append("font_size", font_size);
    form.append("font_family", font_family);

    fetch("/generate", {method:"POST", body:form})
        .then(res => res.json())
        .then(data => {
            document.getElementById("final-video-container").innerHTML = 
                `<video src="/final_videos/${data.video}" controls width="720"></video>`;
        });
}
