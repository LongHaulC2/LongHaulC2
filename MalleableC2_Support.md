# Malleable C2 Support

LongHaul currently implements the network communication layer of Malleable C2 profiles. It focuses on traffic shaping and indicators (http-get, http-post, etc.), while omitting Cobalt Strike-specific payload and artifact configurations.

**Documentation Reference:** [Cobalt Strike Malleable Profile Docs](https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837)

### Custom Extensions (Planned)

LongHaul plans to introduce custom blocks for non-traditional listeners:

* `ntp-get`
* `ntp-post`
* `ntp-config`

### Known Unsupported components:

- beacon specific config settings (ex, ...) - focus is on network portions of malc2
- Multiple profiles in URI strings:
  - `set uri "/include/template/isx.php /include/template/abc.php";`
- Any profile which has the "Cookie" header set on PROTOCOL-POST. This is a WinInet limitation.
- `XOR` transform

### Supported Blocks

#### http-get

Configuration for downloading tasks from the server.

**http-get.server**

* [X] Add on headers (e.g., `header "Content-Type" "image/gif";`)
* [X] Metadata Block (`metadata {}`)

**http-get.server.output**

* *Transform Operations:*

  * [X] `append "string"`
  * [X] `base64`
  * [X] `base64url`

  * [Untested] `mask`

  * [X] `netbios`
  * [X] `netbiosu`
  * [X] `prepend "string"`
* *Termination Options:*

  * [X] `header "header"` (Send data in HTTP header)
  * [X] `parameter "key"` (Send data as URI parameter)
  * [X] `print` (Send data in transaction body)
  * [X] `uri-append` (Append data to URI)

#### http-post

Configuration for submitting data/responses to the server.

**http-post.server**

* [X] Add on headers (e.g., `header "Content-Type" "image/gif";`)
* [X] Output Block (`output {}`)
* [X] ID Block (`uuid {}`)
  **http-post.server.output**

* *Transform Operations:*

  * [X] `append "string"`
  * [X] `base64`
  * [X] `base64url`

  * [Error] `mask` (Currently throws Key Error)

  * [X] `netbios`
  * [X] `netbiosu`
  * [X] `prepend "string"`
* *Termination Options:*

  * [X] `header "header"`
  * [X] `parameter "key"`
  * [X] `print`
  * [X] `uri-append`

#### http-config

Global configuration applied to every HTTP response served by the listener.
*Reference:* [http-server-config](https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845)

* [X] `set headers` (e.g., `set headers "Date, Server, Content-Length, Keep-Alive, Connection, Content-Type"`)
* [X] `header "header"`
* [X] `block_useragents`
* [X] `allow_useragents`

* [Pending] `set trust_x_forwarded_for`

### Unsupported Features

* **http-stager:** Stagers are not supported and are out of scope for this project.

### Global Options

Status of global profile options:

* [ ] `data_jitter`
* [ ] `headers_remove`
* [ ] `jitter`
* [ ] `pipename`
* [ ] `sample_name`
* [ ] `sleep`
* [ ] `sleeptime`
* [ ] `smb_frame_header`
* [ ] `ssh_banner`
* [ ] `ssh_pipename`
* [ ] `steal_token_access_mask`
* [ ] `tasks_max_size`
* [ ] `tasks_proxy_max_size`
* [ ] `tasks_dns_proxy_max_size`
* [ ] `tcp_frame_header`
* [ ] `tcp_port`
* [ ] `useragent` (Global default)

**Removed/Out of Scope:**

* `host_stage`
* `pipename_stager`
