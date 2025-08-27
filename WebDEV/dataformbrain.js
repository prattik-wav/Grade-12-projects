const profilebtn = document.getElementById("toggleProfileBtn");
const profilesection = document.getElementById("profile");
const profiledisplay = window.getComputedStyle(profilesection).display;
            
profilebtn.addEventListener("click",() => {
    const profiledisplay = window.getComputedStyle(profilesection).display;
    if (profiledisplay === "none") {
        profilesection.style.display = "block";
        profilebtn.textContent = "Hide Profile Table";
    }
    else {
        profilesection.style.display = "none";
        profilebtn.textContent = "Show Profile Table"
    }
});

const signupbtn = document.getElementById("toggleSignupBtn");
const signupform= document.getElementById("signup");
const signupdisplay = window.getComputedStyle(signupform).display;
            
signupbtn.addEventListener("click",() => {
    const signupdisplay = window.getComputedStyle(signupform).display;
        if (signupdisplay === "none") {
            signupform.style.display = "block";
            signupbtn.textContent = "Hide Signup Form";
        }
        else {
            signupform.style.display = "none";
            signupbtn.textContent = "Show Signup Form"
        }
});

const form = document.getElementById("signupform");
const table = document.getElementById("profiletable");

const ProfilePicInput = document.getElementById("profilePic");
const previewImg = document.getElementById("preview");

ProfilePicInput.addEventListener("change", function() {
    const file = this.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            previewImg.style.display = "block";
        };
        reader.readAsDataURL(file);
    }
});

form.addEventListener("submit", function(event) {
    event.preventDefault();
    console.log("Form has been submitted successfully!");

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const gender = document.querySelector('input[name="gender"]:checked').value;
    const hobbies = Array.from(document.querySelectorAll('input[name="hobby"]:checked'))
                         .map(h => h.value)
                         .join(", ");
    const country = document.getElementById("country").value;

    const ProfilePicInput = document.getElementById("profilePic");
    const PreviewImg = document.getElementById("preview");
    const pfpfile = ProfilePicInput.files[0];
    if (pfpfile) {
        const reader = new FileReader();
        reader.onload = function(e) {
            PreviewImg.src = e.target.result;
            PreviewImg.style.display = "block";
        };
        reader.readAsDataURL(pfpfile);

        console.log("File name:",pfpfile.name);
        console.log("File size:",pfpfile.size,"bytes");
        console.log("File type:",pfpfile.type);
    };
    const bio = document.getElementById("bio").value;

    
    console.log(name,email,gender,hobbies,country,bio);

    const table = document.getElementById("profiletable");
    const newRow = table.insertRow(-1);

    newRow.insertCell(0).textContent = name;
    newRow.insertCell(1).textContent = email;
    newRow.insertCell(2).textContent = gender;
    newRow.insertCell(3).textContent = hobbies;
    newRow.insertCell(4).textContent = country;
    const PicCell = newRow.insertCell(5);
    if (ProfilePicInput.files && ProfilePicInput.files[0]) {
        const reader2 = new FileReader();
        reader2.onload = function(e) {
            const img = document.createElement("img");
            img.src = e.target.result;
            img.width = 100;
            PicCell.appendChild(img);
        };
        reader2.readAsDataURL(ProfilePicInput.files[0]);
    }
    newRow.insertCell(6).innerText = bio;
});