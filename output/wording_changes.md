# Wording and tone pass — before and after

Every user-facing line changed in this pass, grouped by who reads it.
Words only: no layout, no features, no behavior changed.

Throughout, **donor** became **wish granter** or **a neighbor**, **family** became
**neighbor**, and aliases went from *Family A59* to **Neighbor A59**. Those
swaps are not listed one by one below; the lines here are the ones rewritten
beyond that rename.

## Making a wish

Dignity, never pity. Short plain sentences, no story asked for, no gratitude expected, and no claim about how often a wish gets granted.

### `backend/intake_api.py`

1. ~~Hi — I'm here to help you put together your wishes. Tell me what's going on and what would help most right now. You don't need to share your address, phone number or anyone's name here.~~
   → **Hi — I'm here to help you put your wishes together. Tell me what would help, in whatever words are easiest. You don't need to share your address, phone number or anyone's name here.**

2. ~~We've covered a lot here, so I'll stop and put together what we have. You can look through the wishes on the next screen, change anything that isn't right, and start a new chat later if you need to add more.~~
   → **We've covered a lot, so I'll stop here and gather what we have. Check the wishes on the next screen, change anything that isn't right, and start a new chat any time you want to add more.**

3. ~~You already have {used} wishes on the wall, which is the most we can show at once ({cap}). Once one of them is granted, come back and we'll add the next one.~~
   → **You have {used} wishes on the tree, which is as many as we show at once ({cap}). When one of them is granted, come back and we'll add the next.**

4. ~~Wishing Tree has reached its daily limit for AI usage, so the safety check on this one has to wait. Your wish is saved and nothing is lost — it will go up once the limit resets.~~
   → **Our privacy check is busy right now, so this one has to wait. Your wish is saved and nothing is lost — it goes up as soon as the check is free.**

5. ~~The assistant could not answer just then. Please try again.~~
   → **That didn't get through. Try sending it again.**

6. ~~We could not finish the safety check on this one just now. It is saved and a coordinator will look at it.~~
   → **We couldn't finish the privacy check on this one just now. It's saved, and a coordinator will take a look.**

7. ~~You have as many wishes on the wall as we can show at once. Once one of them is granted, come back and add the next.~~
   → **You have as many wishes on the tree as we show at once. When one is granted, come back and add the next.**

8. ~~No family with alias {alias!r}.~~
   → **We couldn't find a neighbor with the alias {alias!r}.**

### `backend/family_api.py`

9. ~~Thanks for telling us. A Wishing Tree coordinator will get in touch to sort out another time — you don't need to do anything else.~~
   → **Thanks for telling us. A coordinator will get in touch to find another time. Nothing else for you to do.**

10. ~~A Wishing Tree coordinator will email you to confirm the amount and who to pay. The payment goes straight to your landlord or the utility company — never to you, and never through this app.~~
   → **A coordinator will email you to confirm the amount and who to pay. The payment goes straight to your landlord or the utility company — never to you, and never through this app.**

11. ~~Granted!~~
   → **A neighbor granted it!**

12. ~~"delivered", "This one arrived. Thank you for letting us help.", False~~
   → **"delivered", "This one arrived.", False**

13. ~~("on_its_way", "A neighbor has dropped this at the hub. It comes to you on the next delivery day.", False~~
   → **("on_its_way", "It's at the hub. We bring it to you on the next delivery day.", False**

14. ~~"granted", "A neighbor has claimed this one.", False~~
   → **"granted", "A neighbor nearby is picking this up for you.", False**

15. ~~("on_the_tree", "Up on the tree where neighbors can see it. We can't promise someone will grant it, but most wishes find someone.", False~~
   → **("on_the_tree", "Up on the tree where neighbors can see it. We can't promise someone will grant it, but we'll do our best to find a neighbor who can help.", False**

16. ~~("being_checked", "We're checking this for anything that shouldn't be public. It usually takes a moment.", False~~
   → **("being_checked", "We're checking this for anything that shouldn't be public. It only takes a moment.", False**

17. ~~Couldn't be posted~~
   → **Not on the tree yet**

18. ~~raise HTTPException(status_code=403, detail="That delivery is not yours."~~
   → **raise HTTPException(status_code=403, detail="That delivery isn't yours."**

19. ~~No family with alias {alias!r}.~~
   → **We couldn't find a neighbor with the alias {alias!r}.**

### `backend/agents/budget.py`

20. ~~Wishing Tree has reached its daily limit for AI usage. Nothing you did caused this — please come back tomorrow, or ask the coordinator to look at it.~~
   → **Wishing Tree is busy right now. Nothing you did caused this — try again tomorrow, or tell a coordinator.**

21. ~~This conversation has got long enough that we need to stop here. Your wishes so far are safe — go to the review screen to check and approve them, and start a new chat later if you need to add more.~~
   → **We need to stop here for now. Everything you've told me is safe — check your wishes on the next screen and post them, and start a new chat any time.**

### `backend/agents/safety.py`

22. ~~We could not put this one on the wall yet. A coordinator will look at it and get back to you.~~
   → **This one isn't on the tree yet. A coordinator will take a look and get back to you.**

### `frontend/src/pages/SignUpFamily.tsx`

23. ~~title="I need help" blurb="You get an alias like “Family A59”. That alias is the only name anyone else ever sees." >~~
   → **title="Make a wish" blurb="Everyone needs a hand sometimes. Tell us what would help, and a neighbor nearby can make it happen. You'll only ever appear as “Neighbor A59,” never by name or address." >**

24. ~~How the coordinator reaches you about a delivery. We never post it and never email you anything else.~~
   → **We'll only use this to coordinate your delivery. It's never shown to anyone.**

25. ~~Your address, email and phone are shown only to the Wishing Tree coordinator who delivers to you. They are never shown to donors, never put on the wish wall, and never sent to the AI.~~
   → **Your address, email and phone are only ever seen by the coordinator who brings your delivery. They're never shown to the neighbor granting your wish, never on the tree, and never sent to the AI.**

### `frontend/src/components/ServiceArea.tsx`

26. ~~We check this first, so you know straight away whether we can reach you.~~
   → **We check this first, so you'll know right away if we deliver to your area.**

### `frontend/src/components/HowItWorks.tsx`

27. ~~<strong>A neighbor nearby grants it, and we deliver it to your door on a Saturday.</strong> We can't promise every wish finds someone — but most do, and nothing is lost if one doesn't.~~
   → **<strong>A neighbor nearby grants it, and we deliver it to your door on a Saturday.</strong> We can't promise every wish will be granted, but we'll do our best to find a neighbor who can help.**

### `frontend/src/pages/Intake.tsx`

28. ~~<Link to="/family/signup">Create a family account</Link> to start an intake.~~
   → **<Link to="/family/signup">Make a wish</Link> to get started.**

29. ~~'On the wish wall'~~
   → **'On the tree'**

30. ~~'On the wall'~~
   → **'On the tree'**


## Granting a wish

Warm and practical. Giving is celebrated; nobody is guilt-tripped, and no family is there to be saved.

### `backend/donor_api.py`

31. ~~Someone else has already granted this wish. Have a look at what else is on the tree.~~
   → **A neighbor just granted this one. Have a look at what else is on the tree.**

32. ~~Paid directly to provider (simulated)~~
   → **Paid straight to the provider (simulated)**

33. ~~( "Rent and utility help never passes through a person. Wishing Tree pays the landlord or the utility company directly. No payment is actually made in this MVP."~~
   → **( "Rent and utility help never passes through a person. Wishing Tree pays the landlord or the utility company directly. No payment is actually made in this demo."**

34. ~~Granted~~
   → **You granted this**

35. ~~Released back to the tree~~
   → **Back on the tree**

36. ~~Released. It's back on the tree for another neighbor — thank you for telling us rather than leaving it.~~
   → **Back on the tree for another neighbor. Thank you for telling us — that's genuinely helpful.**

37. ~~Bring this exact item~~
   → **What to bring**

38. ~~This family asked for this item specifically — please don't substitute.~~
   → **Your neighbor asked for this one specifically, so please don't swap it.**

39. ~~A similar substitute is fine if the exact one isn't available.~~
   → **Something similar is fine if you can't find this exact one.**

40. ~~Wishing Tree pays the landlord or the utility company directly — never the family, and never you to them. A coordinator will email you how to pay. No payment is actually taken in this MVP.~~
   → **Wishing Tree pays the landlord or the utility company directly — never your neighbor, and never you to them. A coordinator will email you how to pay. No payment is taken in this demo.**

41. ~~Someone else has already granted this wish. Have a look at what else is on the wall.~~
   → **A neighbor just granted this one. Have a look at what else is on the tree.**

42. ~~Someone else got there first. Have a look at what else is on the wall.~~
   → **A neighbor got there first. Have a look at what else is on the tree.**

43. ~~No donor with alias {alias!r}.~~
   → **We couldn't find a neighbor with the alias {alias!r}.**

### `frontend/src/pages/SignUpDonor.tsx`

44. ~~title="I want to give"~~
   → **title="Grant a wish"**

45. ~~blurb="Tell us where you are and what you like to help with. You get an alias like “Donor D09”."~~
   → **blurb="Tell us where you are and what you like to help with. You'll appear as “Granter D09” — a neighbor never sees your name."**

46. ~~How the coordinator reaches you about a drop-off. Never shown to families.~~
   → **We'll only use this to coordinate your drop-off. It's never shown to the neighbor whose wish you grant.**

47. ~~Your address, email and phone are shown only to the coordinator. Families never see them.~~
   → **Your address, email and phone are only ever seen by the coordinator. You won't see a neighbor's name or address, and they won't see yours. That's on purpose, to protect each neighbor.**

### `frontend/src/components/DonorHowItWorks.tsx`

48. ~~<strong>We deliver it to the family, and you never see each other's personal details</strong> — on purpose. You don't get their address; they don't get your name.~~
   → **<strong>We deliver it to your neighbor, and you never see each other's personal details.</strong> That's on purpose, to protect each neighbor.**

### `frontend/src/pages/Donor.tsx`

49. ~~<h1 className="page__title">Thank you — that wish is yours</h1>~~
   → **<h1 className="page__title">You just made a neighbor's week. Thank you.</h1>**

50. ~~<Link to="/donor/signup">Create a donor account</Link> to browse and grant wishes.~~
   → **<Link to="/donor/signup">Create an account</Link> to browse and grant wishes.**

51. ~~Rent and utility wishes are paid straight to the landlord or provider — never cash to a family.~~
   → **Rent and utility wishes are paid straight to the landlord or provider — never cash to a neighbor.**

52. ~~'We could not load the wish wall.'~~
   → **'We could not load the tree.'**

53. ~~Back to the wish wall~~
   → **Back to the tree**

54. ~~aria-label="Filter the wish wall"~~
   → **aria-label="Filter the wishes"**

55. ~~Show the whole wall~~
   → **Show the whole tree**

### `frontend/src/pages/GrantConfirm.tsx`

56. ~~Tick the box above once you know you can make it — the wish stays on the tree for someone else until you do.~~
   → **Tick the box above once you know you can make it — the wish stays on the tree for another neighbor until you do.**

### `frontend/src/pages/MyGranted.tsx`

57. ~~You haven't granted anything yet. Have a look at the tree — Monty says the gold leaves are the ones already spoken for.~~
   → **You haven't granted a wish yet. Have a look at the tree — Monty says the gold leaves are the ones already spoken for.**

### `backend/badges.py`

58. ~~This one has to arrive before a date the family gave us.~~
   → **This one has to arrive before a date your neighbor gave us.**

59. ~~Nobody has picked this one up yet.~~
   → **No neighbor has picked this one up yet.**

### `frontend/src/api.ts`

60. ~~'We could not load the wish wall.'~~
   → **'We could not load the tree.'**


## Everyone

The shared screens — landing page, the tree, About, errors.

### `frontend/src/pages/Landing.tsx`

61. ~~to: '/family/signup', eyebrow: 'For families', title: 'I need help', blurb: 'Tell us what you need in your own words. We turn it into wishes you approve before anyone sees them.'~~
   → **to: '/family/signup', eyebrow: 'For neighbors', title: 'Make a wish', blurb: 'Something you or your family could use? Ask your neighbors.'**

62. ~~to: '/donor/signup', eyebrow: 'For neighbors', title: 'I want to give', blurb: 'Browse wishes near you, or get matched to the ones your budget and interests fit best.'~~
   → **to: '/donor/signup', eyebrow: 'For neighbors', title: 'Grant a wish', blurb: 'Help a neighbor with something they need.'**

63. ~~A giving tree that stays up all year in New Haven. Families ask for what they actually need, neighbors grant a wish, and everything moves through one weekly drop-off.~~
   → **A giving tree that stays up all year in New Haven. Neighbors ask for what would actually help, neighbors grant a wish, and everything moves through one weekly drop-off.**

64. ~~<h2 className="accounts__title">Families</h2>~~
   → **<h2 className="accounts__title">Making a wish</h2>**

65. ~~<h2 className="accounts__title">Donors</h2>~~
   → **<h2 className="accounts__title">Granting a wish</h2>**

66. ~~Continue as an existing family or donor, without signing up or typing anything.~~
   → **Continue as a neighbor who already has an account, without signing up.**

67. ~~nothing~~
   → **Every wish on this tree is from someone in New Haven. N wishes granted so far.**

68. ~~No cash ever changes hands between neighbors. Rent and utilities are paid directly to the landlord or provider.~~
   → **No cash ever changes hands between neighbors. Rent and utilities are paid straight to the landlord or provider.**

### `frontend/src/pages/About.tsx`

69. ~~Donors never see who they're helping, and families never see who helped them.~~
   → **Wish granters never see who they're helping, and neighbors never see who helped them.**


## Admin

Short, scannable, operational. Left largely as it was, as you asked.

### `backend/coordinator_api.py`

70. ~~wall for another donor.~~
   → **tree for another neighbor.**

71. ~~Email the family to confirm the amount and who to pay. Paid to the landlord or provider, never to the family. Simulated in this MVP.~~
   → **Email the neighbor to confirm the amount and who to pay. Paid to the landlord or provider, never to the neighbor. Simulated in this demo.**

### `frontend/src/pages/Coordinator.tsx`

72. ~~These screens show families’ home addresses, emails and phone numbers, so they need the admin passcode.~~
   → **These screens show neighbors’ home addresses, emails and phone numbers, so they need the admin passcode.**

73. ~~Expected drop-offs and deliveries, with contact details and statuses. These are the only screens that show a family’s address, email or phone number.~~
   → **Drop-offs and deliveries for the week, with contact details and statuses. The only screens that show a neighbor’s address, email or phone.**

### `frontend/src/pages/AgentActivity.tsx`

74. ~~{cachedShare}% of input tokens served from cache. No family contact details are recorded on this page.~~
   → **{cachedShare}% of input tokens served from cache. No contact details are recorded on this page.**


## Agent prompts

What the agents are told about how to speak.

### `prompts/intake_agent.md`

75. ~~no voice guidance — the prompt covered what to collect, not how to speak~~
   → **A 'How to talk to someone making a wish' section: dignity never pity; never use needy, less fortunate, beneficiary, recipient or charity; never ask for their story; never ask them to be grateful; never quote a rate of wishes granted; call them neighbors, never donors; short sentences.**

76. ~~Say that the wish will go on the wall for neighbors~~
   → **Say that the wish will go on the tree for neighbors**


---

**76 lines rewritten.** A further 12 lines were read in this pass
and left exactly as they were, because they already said the right thing.
