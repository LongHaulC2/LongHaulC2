---
slug: /
title: LongHaulC2
hide_table_of_contents: true
hide_title: true
sidebar_class_name: landing-no-sidebar
---

<div className="landing">

<div className="landing-hero">
  <img width="2000" height="200" alt="LongHaulC2" src="https://github.com/user-attachments/assets/174ea327-8bbb-406c-a8b6-aec0e903a22f" />
  <p className="landing-tagline">Quiet and flexible</p>
  <br></br>
  <!--<p className="landing-sub">Most frameworks are built to get you in. LongHaul is built to keep you there.</p>-->
  <div className="landing-cta">
    <a className="landing-btn-primary" href="/LongHaul%20C2%20-%20Quickstart%20Guide">Get Started</a>
    <a className="landing-btn-secondary" href="https://github.com/LongHaulC2/LongHaulC2">GitHub</a>
  </div>
</div>

<div className="landing-cards">

<div className="landing-card">
    <h3>BOF-First Design</h3>
  <p>Zero "traditional" offensive code. Extend capabilities dynamically in memory for minimal detection surface.</p>
  <div className="landing-card-links">
    <a href="/02%20Implants/Commands">Command Reference</a>
    <a href="/02%20Implants/Systems/MemStore">Memory Store</a>
  </div>
</div>

<div className="landing-card">
    <h3>Protocol Mimicry</h3>
  <p>Define <em>every</em> byte that goes over the wire. Your C2 traffic looks like whatever you need.</p>
  <div className="landing-card-links">
    <a href="./06%20Network%20Profiles/Overview">Mimicry Profiles</a>
  </div>
</div>

<div className="landing-card">
    <h3>Split C2 & Protocol Switching</h3>
  <p>Split tasking and exfil over different profiles. Bake in and swap between multiple profiles at will.</p>
  <div className="landing-card-links">
    <a href="02%20Implants/Commands#3-c2-strategy">Profile Switching</a>
  </div>
</div>

</div>

</div>

<hr className="landing-divider" />

<div className="showcase">
  <input type="radio" name="showcase" id="tab-ops" defaultChecked />
  <input type="radio" name="showcase" id="tab-map" />
  <input type="radio" name="showcase" id="tab-profiles" />
  <input type="radio" name="showcase" id="tab-audit" />
  <div className="showcase-tabs">
    <label htmlFor="tab-ops">Operations</label>
    <label htmlFor="tab-map">Engagement Map</label>
    <label htmlFor="tab-profiles">Profiles</label>
    <label htmlFor="tab-audit">Audit Log</label>
  </div>
  <div className="showcase-panels">
    <div className="showcase-panel">
      <p className="showcase-note">Your home base. Task implants, manage sessions, and run operations from one screen.</p>
      <img alt="Operations tab" src="https://github.com/user-attachments/assets/3448a8ce-4a62-41e2-9caf-fcd3c391983a" />
    </div>
    <div className="showcase-panel">
      <p className="showcase-note">Visualize your infrastructure. See implant chains, listeners, and discovered network topology at a glance.</p>
      <img alt="Engagement Map" src="https://github.com/user-attachments/assets/25c86186-8345-48dc-a5ed-018feace4fcd" />
    </div>
    <div className="showcase-panel">
      <p className="showcase-note">Build, modify, and manage Mimicry profiles. Quickly and painlessly define exactly what your traffic looks like on the wire.</p>
      <img alt="Profiles" src="https://github.com/user-attachments/assets/e666511d-8003-4286-b97e-b791b559d1c6" />
    </div>
    <div className="showcase-panel">
      <p className="showcase-note">Full operator accountability. Every action logged, searchable, and exportable.</p>
      <img alt="Audit Log" src="https://github.com/user-attachments/assets/e7c1fc7a-5881-4618-8116-658d7f025a99" />
    </div>
  </div>
</div>
