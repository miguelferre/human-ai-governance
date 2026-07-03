# What this is and how it is known to work

Straight to the point. This is an automatic reviewer of the interaction layer between an AI and the person who uses it. It does not review the model on the inside. It reviews how the system speaks to the user.

The car makes it clearer. When someone buys one, everyone looks at the engine: power, fuel consumption, emissions. That is measured and regulated down to the last screw. But almost nobody asks whether the dashboard is well thought out. Whether the blind-spot warning fires at the right moment or distracts the driver just as they are about to turn. Whether an alert that keeps showing up can be silenced. Whether the driver understands what the car is saying or trusts it blindly.

The same thing happens with AI in healthcare. The governance tools available today (watsonx, Fiddler, Arize and the rest) audit the engine: bias, accuracy, drift, technical explainability. The dashboard is something almost nobody looks at. And the dashboard is exactly where a clinician decides whether to trust the model, correct it or ignore it. That is where automation bias creeps in, along with alert fatigue, the override nobody captures, the warning that arrives at the wrong moment. That is what this reviews.

## What it does

Given the description of a system (what it does, how it is presented to the user, what the people who use it report), it returns a list of problems in that layer. Not textbook problems. Each finding is tied to three anchors. A recognized guideline that is being breached (it uses Microsoft's 18 and Google's guidebook, the de facto standard), the specific point in the system where it happens, and the evidence drawn from the documentation itself. If a finding cannot be supported by evidence, it is not released.

That last part is deliberate. A report full of "improve explainability" or "watch out for bias" is worthless, because it applies to any system. What adds value is "here, on this screen, the score appears prefilled and that pushes the clinician to accept it without thinking". That can be acted on.

## How it is fed

Feeding it does not require writing a report or wrestling with any odd file format. It is three plain-text templates filled in by the people who already know the system. One is filled in by whoever builds or maintains it. Another is the inventory of existing documents. And the third, the one that really makes the difference, is filled in by whoever uses the AI every day.

That voice, the voice of the person who lives with the machine, is the piece no other auditor looks at. Is the output accepted out of inertia? Can it be corrected when it is wrong? Is it ignored outright? Half the story is there. And contrasting what the technical team believes happens with what the user actually experiences is, in itself, a signal that something in that layer does not fit.

Once the three templates are filled in, running `ingest` assembles the dossier on its own, without touching JSON or anything of the sort. That way, preparing the input does not cost as much as doing the audit by hand.

And if a PDF or a model card of the system already exists, there is no need to copy anything by hand. The `prefill` command passes it to the model, which fills in the template with what the document says and leaves blank whatever does not appear, without making it up. A quick review and it is ready. It is the only input step that uses the model; filling in the templates by hand still costs nothing.

## How it is known to work

And now the important part, which is how it is known that this is serious and not smoke.

It was tested against a real clinical case that had already been worked through by hand. A screening system to prioritize referrals to Gastroenterology, with its interaction problems already identified by people. Of the 15 problems a human had found, the reviewer rediscovers 13 or 14 on its own. With no hints. And almost everything it flags is real, with precision around 100%. It does not pad the report with noise to look productive.

The second point is the most reassuring. It was given a well-designed system, one of those with hardly any problems, and it stayed quiet. Zero findings. It did not invent anything to justify that it was working. An auditor that always finds twenty-five faults is useless, because there is no way to know when to believe it.

The third point was to rule out that it was luck specific to that case. More systems were taken from the literature, with problems documented by independent people, and there are now eight sectors that bear no resemblance to one another, from healthcare to aviation, justice, finance and public administration. It extracts the same patterns. It had not memorized the home case.

The fourth point was that it should not depend on how the input is written. The system description was entirely rewritten, the same information but in other words and another format. It extracts the same thing. It understands what it reads, it does not fish for keywords.

Then the bar was raised as high as possible. Three cases were taken where the correct answer was not set by the author, but by an independent body that had already investigated them thoroughly. A real commission, a state auditor, a federal court. The material was provided raw and at arm's length, that is, without the author touching either the question or the solution. Even so it recovers between 70 and 90% of what they flagged, with an average close to 80%. It finds on its own what was found by people who do this professionally.

There is one number that matters most of all, because it is not set by the author. The one grading the exam is a different model from the one generating, so it cannot pass itself, and the whole process is built so that anyone can reproduce it and get the same result. There the reviewer catches 93% of the problems and, of what it reports, 96% is real. And note, with a cheap model doing the heavy lifting. And it is not from a single run: it has been repeated three times per case and comes out practically the same, which rules out a stroke of luck.

## The user's voice, the part that stands out most

The point above was that the jewel is the voice of the person who uses the AI. That is not a hunch, it has been measured on purpose and with an independent judge. The dossiers were taken and that voice was removed, leaving only the technical documentation, the kind anyone would have. And the reviewer goes blinder exactly where it matters: the problems that can only be seen from the experience of the user go from being found eight out of ten times to little more than five. And the more visceral ones, feeling guilty in front of the machine or trusting it to the point of doubting oneself, those disappear entirely without the voice.

Here is the honest nuance: how much is lost depends on the model. A very capable one deduces part of the cognitive layer from the technical profile even when the user does not report it, so the drop is softened; with a weaker one it sinks further (there it reached three out of ten). But the purely lived experience, what no profile hints at, is brought only by the voice. That is why so much emphasis is placed on that second template, it is not filler.

## For whoever signs off on the purchase

One more thing, very down to earth but it carries weight. Whoever approves paying for this is almost never the person who designs the screens. It is governance, quality, compliance. And those people do not reason in design guidelines, they reason in regulation. So the report translates itself into their language. Each problem also comes out pointing to the article of the European AI regulation that applies (the one on transparency, the one on human oversight, which names over-reliance on the machine in so many words) and to the corresponding part of the American framework, NIST. It stops being a design critique and becomes paperwork that can go into their file. It is indicative, not a legal ruling, and the report itself says so to avoid overselling.

And if it has to be shown in a meeting, the report comes out as a self-contained single page that prints to PDF without depending on anything external. Presentable, in short.

## What it is not yet

Being honest. It is not a finished product with a nice button. It is an engine that works and a method that holds up. It already has a cleanup step that removes the obvious repetitions without losing anything along the way, and that has been measured, it does not drop a single one of the problems it already found. Then the fine cleanup was tested, the one that uses the capable model to merge the same problem stated in five different ways. And here is the honest part. It cleans up considerably more, but every so often it merges two problems that were actually distinct, and in an audit that is worse than leaving a duplicate, because it hides something. So for now the safe cleanup stays as the default and the other one is left as an option to review by hand.

What remains is more about finishing than substance. The prefill already ingests the two sources that really matter, a PDF or a model card for the technical profile and a user interview for their experience. Nothing that changes the conclusion, just things that make it pleasant to use.

## The part that might come as a surprise

There is one more thing, and it is the hardest to arrive at. The starting question was whether this needed a modern AI agent, one of those that decide on their own what to investigate and when to stop. The answer, with the data in hand, is no.

A fixed-step process, far simpler and cheaper to maintain, works just as well or better. And it is more reliable exactly when the information provided is incomplete, which in an audit is the norm. The clever agent, when it lacks information, gets ahead of itself, decides it is done and leaves things unchecked. The orderly, boring process checks them all. For something that is going to review clinical decisions, the second option wins without hesitation.

So in one sentence. There is a reviewer that finds almost everything an expert would find, invents nothing, does not depend on the case or on how the input is written, knows how to translate the result for whoever signs off on the purchase, and does it without needing the most expensive machinery. What remains is to polish it so that it is a pleasure to use.
