# Original forum question captures

Status: 20 preliminary candidates. Source confirmation and author labels are pending. Indexed post text is not a live Reddit/Markdown archive. Dates below are the dates displayed by the indexed source.

## NQ01: Automated remediation status

Source: [SI-2(2)](https://www.reddit.com/r/NISTControls/comments/fhjwsf/). Posted 2020-03-12. Retrieved 2026-10-05 UTC.

> SI-2(2)
>
> Looking for guidance implementing SI-2(2) "automated mechanisms for flaw remediation" for MUSA.
> We have a single system, so there is no WSUS for automated checkins.  Currently to perform updates - I have a powershell script that uses the downloaded MBSA cab file to scan against and reports needed updates for the month.  I then go download those updates, manually install using another script that installs all updates that exist in a folder and then reboots, then re-scan again to verify completion.
> I'm debating about putting the script into scheduled tasks that runs at startup just to satisfy this "automated" verbiage.  But it's really quite pointless if I'm also doing it on-demand once a month, and the cab file never changes unless I bring it in anyway.
> OR - Is the fact that I have run a SCRIPT for checking, and another SCRIPT for install satisfy the fact that's "automated?
> Thoughts?

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ02: Process isolation evidence

Source: ["Evidence" for SC-39 (Process Isolation) on Windows 2019](https://www.reddit.com/r/NISTControls/comments/fslmlw/). Posted 2020-03-31. Retrieved 2026-10-05 UTC.

> "Evidence" for SC-39 (Process Isolation) on Windows 2019
>
> So I'm having a bit of a, disagreement shall we call it, with a federal customer about "evidence" for SP800-53's SC-39 control on a Windows 2019 server in AWS.
>
> I maintain that Windows implements this through "normal" process isolation and virtual memory, it's basically baked into the fabric of Windows at the OS level. In fact, the guidance for the control even states "This capability is available in most commercial operating systems that employ multi-state processor technologies." And any isolation at the VM and hardware level would be AWS's issue under their FedRAMP certification and could be inherited.
>
> However, they are asking for "compelling evidence" and the CCI says:
>
> Test: Have a system administrator logon to an information system process (via one address) and attempt to access another process (via a separate address), if available. For example, shared memory (where it is possible for two pieces of the program to look at the same address space in the memory of the information system) and/or queues (where data is pushed/pulled from two separate spaces within the information system).
>
> Recommended Compelling Evidence: Provide evidence and show how the information system maintains a separate execution domain for each executing process.
>
> Can someone please translate that into technical English not auditor English. What evidence do I provide that one process in Windows cannot just willy-nilly corrupt another process in Windows (well, at least not since Windows NT 3.1 in 1993). It's really hard to screen-shot one process not messing with another process.
>
> Thx.

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ03: Alternate processing site applicability

Source: [CP-7 "Alternate Processing Site"](https://www.reddit.com/r/NISTControls/comments/gzbpkg/). Posted 2020-06-09. Retrieved 2026-10-05 UTC.

> CP-7 "Alternate Processing Site"
>
> When is an alternate processing site **really** required?
>
> The instructions for CP-7 say:
>
> > The organization:
> >
> > **CP-7a.**
> >
> > Establishes an alternate processing site including necessary agreements to permit the transfer and resumption of *Assignment: organization-defined information system operations* for essential missions/business functions within *Assignment: organization-defined time period consistent with recovery time and recovery point objectives* when the primary processing capabilities are unavailable;
> >
> > **CP-7b.**
> >
> > Ensures that equipment and supplies required to transfer and resume operations are available at the alternate processing site or contracts are in place to support delivery to the site within the organization-defined time period for transfer/resumption; and
> >
> > **CP-7c.**
> >
> > Ensures that the alternate processing site provides information security safeguards equivalent to that of the primary site.
>
> That seems pretty clear, but does it mean the alternate processing site is an absolute requirement?

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ04: Service account requirements

Source: [800-53: Service Accounts under IA or AC?](https://www.reddit.com/r/NISTControls/comments/hgb890/). Posted 2020-06-26. Retrieved 2026-10-05 UTC.

> 800-53: Service Accounts under IA or AC?
>
> I can not find where 800-53 cover the idea of service accounts and their requirements.  A point in the right direction would be greatly appreciated.

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ05: Responsibility for COTS errors

Source: [SI-11 Error Handling](https://www.reddit.com/r/NISTControls/comments/j3vd1s/). Posted 2020-10-02. Retrieved 2026-10-05 UTC.

> SI-11 Error Handling
>
> The Information System: a. Generates error messages that provide information necessary for corrective actions without revealing information that could be exploited by adversaries; and b. Reveals error messages only to \[Assignment: organization-defined personnel or roles\].
>
> ​
>
> I am reviewing this control for the millionth time and I have come to the following conclusion: This control is the responsibility of the vendor/developer, if my system is all COTS. But if I have any responsibility for development or configuration of error messages, then the control is my responsibility.
>
> So if you are purchasing a COTS product, you just need to identify that you utilize COTS and rely on their implementation.
>
> If you customize the messages, then you need to expound on what you are providing the end user.
>
> If you are creating the messages, then you need to adhere to the requirements are supplemental requirements and document what you provide.
>
> ​
>
> Does this sound reasonable?

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ06: Baseline spreadsheet

Source: [NIST 800-53 Rev. 5 Control Template](https://www.reddit.com/r/NISTControls/comments/jsw3ah/). Posted 2020-11-12. Retrieved 2026-10-05 UTC.

> NIST 800-53 Rev. 5 Control Template
>
> Hi All,
>
> Does anyone have a NIST 800-53 Rev. 5 controls template/spreadsheet to share that you can filter based on low, moderate, or high?
>
> Thank you

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ07: Cloud authorization boundaries

Source: [Looking for help with AC Family re: NIST 800-53 Rev. 5](https://www.reddit.com/r/NISTControls/comments/l510oe/). Posted 2021-01-25. Retrieved 2026-10-05 UTC.

> Looking for help with AC Family re: NIST 800-53 Rev. 5
>
> Hi All,
>
> First time poster here, looking for some help with my first real go around with 800-53 (specifically rev 5!).
>
> So I am having some trouble with the AC family, and identifying my scope. Lets say hypothetically I know for a fact what my authorization boundary is, and that it includes multiple systems as our solution is a cloud based PaaS that has a number of related SaaS that are used for respective aspects of our services (e.g., logging/monitoring, CI/CD, ticketing, etc.).
>
>
> Now, the language of this control family is not helpful -- what is "the system"? A lot of these controls would be a lot easier for me to put my hands around if they were scoped to just our platform, but i was under the impression I have to apply these controls to my full authorization boundary, so I am not even sure if some of the bits of my authorization boundary that I dont even control can handle some parts of AC-2 or AC-6. This gets even more confuzzling when you add in the cloud element of this all, so I would really appreciate any thoughts or suggestions on the matter.
>
> Thanks!
>
> \-35

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ08: FedRAMP requirements

Source: [800-53 vs FedRAMP](https://www.reddit.com/r/NISTControls/comments/xlkw24/). Posted 2022-09-23. Retrieved 2026-10-05 UTC.

> 800-53 vs FedRAMP
>
> Pardon the newbie question - but what's the difference between these two.
>
> Is FedRAMP satisfied by 800-53 moderate controls?

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ09: Small-system audit logging

Source: [Setting up auditing/logging for NIST 800-53](https://www.reddit.com/r/NISTControls/comments/10fn11g/). Posted 2023-01-19. Retrieved 2026-10-05 UTC.

> Setting up auditing/logging for NIST 800-53
>
> I'm securing a very small home-security company (only need to secure one machine) for NIST controls to hold CUI, and I downloaded Kiwi Syslog for the SIEM. However, I'm not sure what logging/auditing rules on my SIEM I need to set-up in order to be compliant with the "Audit and Accountability" section. Are there any clear resources out there?

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ10: SCIF control selection

Source: [NIST 800-53 Controls](https://www.reddit.com/r/NISTControls/comments/11agrl6/). Posted 2023-02-24. Retrieved 2026-10-05 UTC.

> NIST 800-53 Controls
>
> I've been reading up on my NIST 800-53, but I am still a bit confused about which controls within a control family are picked for any given SCIF classification level or high water mark.
>
> Been going back and forth with another coworker if continuous enforcement is required or not. BTW, we're following DISA/DAAPM.

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ11: Malware response selection

Source: [SI-3 2. Rev 5](https://www.reddit.com/r/NISTControls/comments/13iknc0/). Posted 2023-05-15. Retrieved 2026-10-05 UTC.

> SI-3 2. Rev 5
>
> How many actions are you seeing for this security control requirement:
>
> \[Selection (one or more): block malicious code; quarantine malicious code; take \[Assignment: organization-defined action\]\]; and send alert to \[Assignment: organization-defined personnel or roles\] in response to malicious code detection; and
>
> I see three:
>
> 1. Block malicious code or quarantine malicious code
> 2. take an organization-defined action
> 3. Send alert to personnel or roles
>
> I was told this is two actions only:
>
> 1. Block malicious code or quarantine malicious code or take an organization-defined action
> 2. Send alert to personnel or roles

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ12: Session termination limits

Source: [Session termination time (3.1.11, AC-12, SC-10) - how long is too long?](https://www.reddit.com/r/NISTControls/comments/143p053/). Posted 2023-06-07. Retrieved 2026-10-05 UTC.

> Session termination time (3.1.11, AC-12, SC-10) - how long is too long?
>
> > NIST 800-171 rev 2 Terminate (automatically) a user session after a defined condition.  3.1.11[b] user session is automatically terminated after any of the defined conditions occur
>
>
>
> > NIST 800-53 rev 5 AC-12 Automatically terminate a user session after [Assignment: organization-defined conditions or trigger events requiring session disconnect].
>
>
>
> > NIST 800-53 rev 5 SC-10 Terminate the network connection associated with a communications session at the end of the session or after [Assignment: organization-defined time period] of inactivity.
>
>
>
>
>
> I am clear what these ask.  Terminate network connection and terminate user session after a period (or other trigger events, but I am looking for time in this case).
>
> * What is an *organization-defined* time period that will not come across as malicious compliance? That is, if we define the period to be 364 days, is that acceptable? Why, or why not?
>
> * Is there an Government definition somewhere (like 32 CFR 236.2 defines 'rapidly respond' as no more than 72 hours)?

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ13: PCI DSS crosswalk

Source: [Control map from PCI DSS to/from 800-53 r5?](https://www.reddit.com/r/NISTControls/comments/15eiini/). Posted 2023-07-31. Retrieved 2026-10-05 UTC.

> Control map from PCI DSS to/from 800-53 r5?
>
> My organization wants to use 800-53 r5 as our primary control catalog. We also have PCI DSS obligations.
>
> Is there some kind of authoritative, published mapping between the PCI DSS controls and the 800-53 r5 controls?
>
> We would much rather implement, assess ourselves against, and generally “speak” 800-53 r5  internally, and then translate to other control frameworks as required when we have external obligations. I realize there might not be a 1-to-1 mapping of every single idea between control frameworks, but we’re just looking for a pointer in the right direction.

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ14: Operational defects and remediation

Source: [Operational bug controls](https://www.reddit.com/r/NISTControls/comments/1ay1tbl/). Posted 2024-02-23. Retrieved 2026-10-05 UTC.

> Operational bug controls
>
> Hello r/NISTControls!
> Our organization recently suffered a massive outage due to an IT vendor's operational bug.  This was \*not\* a CVE.  I'm fairly familiar with all of the cybersecurity controls surrounding CVEs or security vulnerabilities.  Can someone point me to controls that would mitigate against a bug like this for example:
> https://bst.cisco.com/quickview/bug/CSCwf08698
>
> You'll see that this is not a CVE and none of the security vulnerability solutions would address it.  Here are the controls I found, but my concerns that they won't address the risk:
>
> 1. SI-2 has the word 'vulnerability' in it and that's usually associated with CVEs (same rationale for SI-2(2) and SI-2(3))
> 2. SI-7 doesn't seem to fit because it wasn't an unauthorized change
> 3. CM-2 doesn't apply because this bug was not announced from the vendor prior to when the asset was placed into service.
>
> Traditionally patch management solutions address operating system bugs/flaws/patches so references to patch management doesn't seem right.
>
> Follow up question - how are your organizations tracking bugs if your CVE solutions aren't addressing them?  Ideally in an automated fashion.  And I'm not talking about the operating system (server/desktop) level.
>
> Thank you in advance!

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ15: Assigning controls to system types

Source: [NIST 800 - 53 Implementation](https://www.reddit.com/r/NISTControls/comments/1btyzmt/). Posted 2024-04-02. Retrieved 2026-10-05 UTC.

> NIST 800 - 53 Implementation
>
> Hello everyone,
>
> I have just implemented the NIST 800 53 for my employer in Germany. In other words, I have written a large catalog of safety measures (>400 controls) based on NIST 800 -53.
>
> We are now planning to inventory all IT systems and assign a subset of relevant safety measures to each IT system.
>
> My problem is that I don't want to assign controls individually for a large number of IT systems and applications.
>
> Hence my question:
>
> Is there a methodology from NIST on how I assign controls from the NIST 800 - 53 to categories of IT systems or applications? For example, is there a template that certain Control Families are relevant for web servers?
>
> Thanks in advance!

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ16: Audit storage parameter

Source: [Help me understand control tailoring](https://www.reddit.com/r/NISTControls/comments/1bz0n8c/). Posted 2024-04-08. Retrieved 2026-10-05 UTC.

> Help me understand control tailoring
>
> I was reading through NIST SP 800-53 R5, and was looking at the example of a control on page 9 of the PDF. I understand the basic structure. However, I don't think I understand how to tailor the control. The base control says:
>
> > Control: Allocate audit record storage capacity to accommodate \[Assignment: organization-defined audit record retention requirements\].
>
> What exactly am I supposed to be filling up within the square brackets? Is it supposed to be in days? Is it supposed to be in TBs? Which of the following is correct?
>
> Allocate audit record storage capacity to accommodate 60 days of logging.
>
> Allocate audit record storage capacity to accommodate 1 TB of logs.
>
> Allocate audit record storage capacity to accommodate 1 TB of logs per day.
>
> Allocate audit record storage capacity to accommodate \[something else?\]
>
> Also where do I record justifications while tailoring the control?
>
> Should I put it like this: Allocate audit record storage capacity to accommodate 60 days of logging as per our internal policy.

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ17: Self-assessment workflow

Source: [Looking for a little help with self-assessment of 800-53r5](https://www.reddit.com/r/NISTControls/comments/1civ1d0/). Posted 2024-05-03. Retrieved 2026-10-05 UTC.

> Looking for a little help with self-assessment of 800-53r5
>
> I’m sys admin with very limited experience in information security/documentation. I was tasked to self-assess my company controls and document my findings. Is there an online resource that provide guidance to do this?
>
> I found the official assessment guide 800-53A and was thinking of creating an interview template to review specific controls with the system admin/owner. Once I have the info and evidence, update the 800-53A with my findings.
> Is this the correct approach?
>
> TIA

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ18: Concurrent session control

Source: [NIST SP 800-53 AC -10 - Practical example](https://www.reddit.com/r/NISTControls/comments/1d1yhdk/). Posted 2024-05-27. Retrieved 2026-10-05 UTC.

> NIST SP 800-53 AC -10 - Practical example
>
> Hello everyone,
>
> I need help with the Control AC - 10 of the NIST Sp 800 -53!
>
> Can someone explain to me with a practical example what the control intends?
>
>
>
> As I understand it, the intention of the control is that admins in particular are only allowed to establish a limited number of sessions for example with an application?
> In other words, an admin may only have a few simultaneous sessions in an ERP system?
>
> Is this realistic in your experience? I have discussed this control with my admins and I encountered very fierce resistance...
>
>
>
> Thank you very much!

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.

## NQ19: Policy content and account types

Source: [Writing Good Policies](https://www.reddit.com/r/NISTControls/comments/1els2x6/). Posted 2024-08-06. Retrieved 2026-10-05 UTC.

> Writing Good Policies
>
> Hey all,
>
> Working on 800-53 policies and an SSP in preparation for going for FedRAMP authorization and I'm tripping up over the actual purpose of policies. I've written policies so far that are basically just a copy/paste of the controls saying "we must do x or y". I think these will get through audit, but I'm not totally satisfied they're good policies.
>
> For example, AC-2 (a) - "Define and document the types of accounts allowed and specifically prohibited for use within the system".
>
> The simple policy is - "The types of accounts allowed or prohibited from accessing the system must be defined and documented". Great, but this doesn't actually define the types of accounts that are allowed/prohibited. Isn't this just the same as a policy saying "We need to implement \[control\]" 400 times?
>
> In this way, I see pieces of documentation doing the following things, with some overlaps:
>
> * 800-53 controls - this is what you must do.
> * Policies - this is what we must do.
> * Procedures - this is how we do things.
> * SSP - this is what we do, who does the thing, and how it meets the control.
>
> A different policy is - "\[Company\] allows individual and service accounts. Shared, group, and emergency accounts are prohibited in \[System\]". Ok, so the types of accounts are defined, but now the policy doesn't say what we have to do. Is that ok if the whole point is complying with 800-53, which already defines what we have to do?
>
> In this way I see documentation doing the following things, still with overlaps:
>
> * 800-53 controls - this is what you must do.
> * Policies - this is what we do.
> * Procedures - this is how we do things.
> * SSP - this is what we do, who does the thing, and how it meets the control.
>
> Either way there's overlap between roles of documentation.
>
> Or are the controls themselves not technically considered and it all has to be "in house" so to speak?
>
> * Policies - this is what we must do.
> * Procedures - this is how we do things.
> * SSP - this is what we do, who does the thing, and how it meets the policy.
>
> This feel quite rambly and might not make any sense, hopefully it's clear enough though.

Capture note: Stopped at the question author's closing sentence. The indexed result then blends in unmarked reply text about Eramba, which is excluded.

## NQ20: Logout and device lock

Source: [800-53 AC-2(5) Logout Versus Lock](https://www.reddit.com/r/NISTControls/comments/1fyhvpg/). Posted 2024-10-07. Retrieved 2026-10-05 UTC.

> 800-53 AC-2(5) Logout Versus Lock
>
> https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-2/ac-2-5/
>
> > Require that users **log out** when \[Assignment: organization-defined time period of expected inactivity or description of when to log out\].
>
> # Supplemental Guidance
>
> > Inactivity logout is behavior- or policy-based and requires users to take physical action to log out when they are expecting inactivity longer than the defined period. **Automatic enforcement of inactivity logout is addressed by AC-11.**
>
> **However**, AC-11 is not about Log out, it's about Device Lock!
>
> https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-11/
>
> >
> Prevent further access to the system by \[Assignment (one or more): initiating a device lock after \[Assignment: organization-defined time period\] of inactivity, requiring the user to initiate a device lock before leaving the system unattended\]; and
>
> > Retain the device lock until the user reestablishes access using established identification and authentication procedures.
>
>
> So my question is this. Is AC-2(5) actually asking for us to put in place a policy that users **log out** their computer at the end of the day, or would it be sufficient to say that users must **lock** their computer when they walk away from it?

Capture note: Captured question block before the next visible dated comment. Original Reddit Markdown and live edit history are not available from this retrieval.
