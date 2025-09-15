function login() {
    const username = document.getElementById("username").value;
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/login", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.withCredentials = true;
    xhr.onload = () => {
        if (xhr.status === 200) {
            document.getElementById("login-section").style.display = "none";
            document.getElementById("file-section").style.display = "block";
        } else {
            alert("Login failed");
        }
    };
    xhr.send(JSON.stringify({ username }));
}

function logout() {
    const xhr = new XMLHttpRequest();
    xhr.open("DELETE", "/api/login", true);
    xhr.withCredentials = true;
    xhr.onload = () => {
        if (xhr.status === 200) {
            document.getElementById("login-section").style.display = "block";
            document.getElementById("file-section").style.display = "none";
            document.getElementById("files").innerText = "";
            alert("Logged out successfully.");
        } else {
            alert("Logout failed.");
        }
    };
    xhr.send();
}


function listFiles() {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/list", true);
    xhr.withCredentials = true;
    xhr.onload = () => {
        console.log("Status:", xhr.status);
        console.log("ResponseText:", xhr.responseText);

        const filesDiv = document.getElementById("files");

        if (xhr.status === 200 && xhr.responseText.trim() !== "") {
            filesDiv.innerText = xhr.responseText;
        } else if (xhr.responseText.trim() === "") {
            filesDiv.innerText = "No files found on the server.";
        } else {
            filesDiv.innerText = `Error: ${xhr.status}`;
        }
    };
    xhr.onerror = () => {
        console.error("Request failed");
        document.getElementById("files").innerText = "Failed to fetch file list.";
    };
    xhr.send();
}


function getFile() {
    const filename = document.getElementById("fileToGet").value;
    const xhr = new XMLHttpRequest();
    xhr.open("GET", `/api/get?file=${filename}`, true);
    xhr.responseType = "blob";
    xhr.withCredentials = true;
    xhr.onload = () => {
        const url = window.URL.createObjectURL(xhr.response);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
    };
    xhr.send();
}

function deleteFile() {
    const filename = document.getElementById("fileToDelete").value;
    const xhr = new XMLHttpRequest();
    xhr.open("DELETE", `/api/delete?file=${filename}`, true);
    xhr.withCredentials = true;
    xhr.onload = () => {
        alert(xhr.responseText);
    };
    xhr.send();
}

function uploadFile() {
    const fileInput = document.getElementById("fileToUpload");
    const file = fileInput.files[0];
    if (!file) {
        alert("Please choose a file to upload.");
        return;
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/push?file=${encodeURIComponent(file.name)}`, true);
    xhr.withCredentials = true;
    xhr.onload = () => {
        alert(xhr.responseText);
    };

    const reader = new FileReader();
    reader.onload = function () {
        const arrayBuffer = reader.result;
        xhr.send(new Uint8Array(arrayBuffer));
    };
    reader.readAsArrayBuffer(file);
}
