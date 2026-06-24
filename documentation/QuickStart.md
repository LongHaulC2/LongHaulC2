---
id: LongHaul C2 - Quickstart Guide
slug: /
---

# Quickstart Guide

What's up! If you just want to get rolling with the tool, this is the page for you!

## Quick Links

Get up to speed and join the development with the links below:

* **[GitHub Org](https://github.com/LongHaulC2):** Explore the source code, track issues, and submit pull requests.
* **[Video Documentation](#):** *(Coming Soon)* Check out our YouTube channel for visual setup guides, usage tutorials, and more.
* **[Doxygen](https://longhaulc2.github.io/doxygen):** DoxyGen Implant Documentation
<!-- * **[Documentation](#):** *(Coming Soon)* Everything you need to deploy, configure, and operate LongHaul. -->
* **[Latest Releases](#):** *(Coming Soon)* Grab the latest binaries and update notes.


<!--* **[Community Discord](#):** *(Coming Soon)* Join the conversation, ask questions, and share your setups.-->

---


## Getting Started

I'll keep this short because I hate long install instructions. 

First, verify you have the following:
* **A Linux box**
    * **With `sudo` privileges**
* **An internet connection**
* **A brain (optional)**

### 1. Install and Start the Server

Run these commands to pull the code, install the dependencies, and fire up the backend:

```bash
git clone https://github.com/LongHaulC2/LongHaulC2
cd LongHaulC2

# install make
sudo apt-get install make

# Setup everything
make deploy

# Done!
# check status with:
sudo systemctl status longhaulc2-web
sudo systemctl status longhaulc2-server
```

### Additional Docs:
You can find the more in-depth setup docs here:

[Setup Docs](https://longhaulc2.github.io/00%20Intro%20&%20Setup/LongHaul%20C2%20-%20Advanced%20Setup)