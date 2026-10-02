yt_transcript = """
Hello community! You know, we always try to improve our large language model.
And you know, a year ago, Stanford University gave us here DSPy, a self-improving machine
learning system. But now, some days ago, Stanford published their latest research,
and it is called TextGrad. And it is able to do an automatic differentiation via text.
Now, TextGrad, and you get it, is of course a reference to AutoGrad. In AutoGrad, we have
access to the tensors within the layers of our large language model. Now, with TextGrad, we do
not have access. Think about GPT-4 Omni, where we cannot dive here into the specific layer structure,
into specific tensors. So therefore, what we do, or what Stanford did, is invent a code extension
to PyTorch, and all is now open source, and you can use it. And to give you here the overview,
what we have, more or less, we have two AI systems. Let's say, on the one hand side,
we have GPT-4 Omni, and the other one, we have the GPT system, or any other open source LLM that you
like, that we want to optimize. So how does it work? Easy. We have API calls between those LLM
systems, and the task is simple, to find the best prompt. So we are at programming here, prompt
engineering, for a very specific task on exactly this LLM. Now, you know that this is now a very
sensitive topic, given that this, let's say it's GPT-3.5, has a given pre-training. It has a given
fine-tuning. It was given instruction how to behave. It was given an alignment, like DPO,
how to behave as a system in the responses. It was trained on an instruction set with a given
complexity, and it is only to solve up to a certain level of reasoning task, given all the
pre-training that's happened. But you know immediately, you understand, that this also
is valid here for our more intelligent LLM, our evaluator, our teacher LLM. So this is now an
interesting play, where we have now, very code simple in a PyTorch extension, to do this
automatically. Now, to give you the final result, I use this now, I code this now for a week,
and I have to say, in my domain, science, for my task, very much logical reasoning,
TextGrad is significantly better performant than DSPy. So let's have a closer look at this.
We will start with AutoGrad, just for my green grasshoppers to remember this, then DSPy, and then we focus on natural language gradients, which is here something beautiful in
TextGrad, and then I show you the new code extension, and I give you four notebooks that
you can try it out yourself immediately, and it is open source. So for my green grasshoppers, hello,
great that you are back. Now, I know that you know how AutoGrad works, but just to have you
at a certain level that we all know, we have a forward pass, the neural network makes prediction by processing the input data to its layers, and this pass computes the loss function, which measures
the difference between the network's prediction and the actual target values. Now, during the
forward pass, the AutoGrad system records all the operation performed on the tensors in a direct
acyclic graph, and you know it. Now, in the backward pass, once the forward pass is completed,
the loss is calculated, the backward pass begins, and AutoGrad computes the gradients of the loss
function with respect to each tensor, each parameter that contributes to the loss. This is
done by traversing the DAC from the loss tensor back to the input tensor, and using a simple chain
rule of calculus, the AutoGrad accumulates here the partial derivatives of the loss function with respect to each tensor. And then we do simply a gradient update. Now, you know that this is,
if you want, the computational mathematical view of this, and now we take exactly this logic,
this pseudo code, if you want, and we build on this. The core feature of AutoGrad, if you
remember, is its ability to perform automatic differentiation. This means it can automatically
compute derivatives of complex function, and this is, of course, essential for our deep neural
network operation. Plus, remember in PyTorch, those AutoGrad systems use a dynamic computation
graph, which are built on the fly during the forward pass, and this is exactly what we need
and what Stanford implemented now in its new methodology. So, two points to remember,
automatic differentiation by the system and a dynamic computation graph structure.
Now, if you go to GitHub, here you are, TextGrad, it is beautiful because, as I told you, it is
open source. It is an AutoGrad engine, but now, since we do not have access to the tensors itself
for textual gradients. More or less, that's all there is to it. However, the implementation is
really beautiful. So, let's have a look at this. Those are the two contributors. Thank you for
publishing this and making it open source for the community. It is done in Python, as you can see, and here you have the GitHub link for you to discover this yourself.
Just to show you, they operate here with an analogy, and it is a very abstract form,
but it is very helpful because they say what we have. Normally, we have an input, we have a model,
our LLM, then we calculate the loss function, and we have an optimizer, Adam, for example.
So, in mathematical terms, this is easy. Those are the four elements. Now, in PyTorch, remember,
cross entropy loss and gradient descent? You know this from PyTorch. And now, in text grad,
they follow this idea here in PyTorch implementation really close by. So, what we
have here now, the input is now a variable, the model is a black box LLM, the loss is now a text
loss since we can only operate with the input and output of proprietary LLMs, and our optimizer is
now something beautiful. It is a text gradient descent module. And more about this in a minute.
Now, Stanford tells us, hey, if you know PyTorch, you know 80% of text grad.
You know, I am coding this now for more than a week. I have to tell you, no, this is not correct. You know 20% of text grad, but more about this later. So, what is nice, Stanford gives us here
four colab networks that you can jump in. I would recommend you start immediately with a number one,
and then you move here to prompt optimization. Try it out yourself, get your hands here deep into
the code, but it is a beautiful implementation. And it is very powerful. And if you missed out
on DSPy, the good thing is it is built on DSPy, and now it's a year later, and now you have all
those optimizations and maybe even clearer implementation now in this particular code.
So, here, you see a very short Python program. This is all. This is number three. Here is the
prompt optimization. You install here pip install textgrad. Then you have, yeah, you need an open
API key, of course, where you have to pay OpenAI that you can use here, the GPT-4o system, the Omni
system, and what we want to optimize the prompts are for a system that's not so intelligent. So,
GPT-3.5-20125. Great. So, you see, you run here through this. You define here the different
function, the evaluation set, the validation. Yes, and then you have everything from the train, validation, and test data set. And then you start here with example here, the data loader. You know
all of this. And then you just let the system run and optimize itself. So, the code is rather easy,
but we have to understand what is happening here behind the code. How is this possible that text
grad is working so beautifully? Now, what they tell us, they had two main inputs to design
to create the new model. And the first input was, of course, DSPy. So, the idea of using a complex
LLM-based system as programs with many layers, and this proposes a way to build and optimize them in
a programmatic fashion. And after a year, yes, this is DSPy here. You have the GitHub. You have here
a call-up notebook to get started, or you have a look here at my playlist. I have a playlist with
eight videos. I explain DSPy. I show you the program, the AI pipelines. I show you here,
if you use ICL rec classification, I explain the code to you. And I give you even a little bit
outlook how to improve the system. But the second part is now a part I have never shown you on this
channel. And this is also new to me. And this is prompt optimization with textual gradients,
Prodigy. Now, Prodigy, you have to be careful, because this is the key to understand here this
new methodology. And I tried to read it without understanding what Prodigy is, and I failed.
So, Prodigy is built on the textual gradient analogy. And I tried to implement it, but no,
they just use here the analogy of it, and they implement it in a much simpler way than you would
imagine. But of course, this analogy is here what we call now automatic differentiation on text.
So, let's have a look at this maybe. This is the original study, Microsoft Asia AI. A very nice
study, I would recommend you read it, although it's from October 2023. And they explain here
in detail the automatic prompt optimization with gradient descent and beam search. Now,
let me give you three main facts you have to know about it. It acts here like a numerical
gradient calculation, but now we are not in the numerical space, but now we are operating in the
semantic space. But since we do not have access to the vector representation of the semantic space,
we have to use here simply the sentences. So, we are now operating here on a semantic level,
but what they do, they generate here through a feedback loop where the LLM critiques the current
prompt, either from itself, but better is you have two LLMs by identifying and describing its
shortcoming. So, you have one teacher LLM like GPT-4, and the other one is GPT-3.5, whatever you
have on an open source LLM. And this more intelligent LLM identifies and describes the
shortcoming given a specific task to GPT-3.5 and how GPT-3.5 responds. And then we run to a
cycle of self-improvement. So, prompt editing, so adjusting now the next iteration of a maybe
better prompt by addressing the issues highlighted by the natural language gradients, uses another
set of LLM instructions to modify the prompt in a way that it moves, careful, semantically opposite
to the problem described by the gradients. So, if, let's say, GPT-4 says, hey, GPT-3.5,
in your answer you didn't, you forgot a fact, yeah? So, now the instruction from GPT-4 to GPT-3 is,
hey, semantically opposite to the problem, include now new facts, maybe include this specific fact,
analyze this specific sector that you forgot to analyze, and of course, described here by
textual gradients. And this is exactly what this is all about in this topic. Yeah, then you have
beam search and bandit selection, which is not so important, but what it does now in a summary,
this now prodigy integrates learning from mistake through feedback on existing prompts with a
strategic exploration of new prompt configuration. Imagine beam search, aiming to find the optimal
configuration or the optimal prompt structure in fewer steps, and it does this in a more intelligent
way than in DSPy and a different methodology. However, honestly, this requires quite some API
calls happening between those systems, which can be computational expensive. So, I would recommend
you do it once here to find an optimal prompt structure for one particular problem, and then
you can reuse this particular prompt. And I will show you an example in a second. Okay, for my green grasshoppers, so what we have, we have an LLM that generates something. This
giant model, let's say, GPT 3.5, generates an initial response based on the current prompt.
And you might consider this the primary LLM prompt that you are trying to optimize, but not you
handcrafted as a human, but you ask the help of another LLM, let's say, GPT 4, and then operates
per processing input data according to the existing prompt and generate output data then and generate output data then assessed for their quality and accuracy, assessed by the critique
LLM or GPT 4 or whatever you like. So, this new model critiques the output from the generation LLM.
It analyzes how well the prompt guided the generation of response and identifies the specific
weaknesses in the prompt. And then the critique LLM generates what the method refers to as natural
language gradients. This is important. Natural language gradients, which are essentially
detailed feedback on how the prompt could be altered to yield a better response. And you see,
this is exactly here when we have a gradient descent. Now we go exactly in the semantic space
in a different direction. So, this feedback mimics the function of the gradients into traditional
autograd numerical optimization by pointing out the direction which the prompt should be modified
in order to improve its performance, but you immediately understand what is here the limitation.
GPT 4 thinks it is in its own way, but GPT 3.5 is only able to handle a certain complexity level
of tasks. Now, if you prefer to see this, what I just explained to you verbally in a pseudocode,
from the publication here you have the complete pseudocode of Prodigy.
Now, for example, line five here is explained here a little bit more in detail, and then you have line
seven explained, and then another line seven here in the algorithms explained even further.
So, if you like the visualization of a pseudocode to help you thinking through this,
this is the way to do it. Now, let me come back here to this concept of modifying a prompt to move
semantically opposite, because this is not where you say, hey, this is a mathematical clear definition.
So, what we want to do, we want to improve here the performance of the model, the output that
is generated, but not by learning new facts or learning new knowledge or having a new pre-training,
but through prompt optimization, prompt engineering. But now we want to do this here
in an automatic way with the natural language gradient optimization. And this process here
mimics, this is the analogy, the numerical gradient descent, but is here applied in the
semantic or language-based context. Beautiful. As I told you, it all depends on the cleverness
of the LLMs, or to be more specific, on the pre-trained complexity level that this LLM is able
to handle and analyze. And if a gradient descent that a prompt is too weak, make it more specific,
would be a move in the opposite direction. So, whatever GPT-4 notices here in the output of GPT
3.5, it tries to move in the opposite direction, whatever this is. And since we are here in the
semantic space, it all depends here now, let me put it in a more mathematical way, in the
vector embeddings of the semantic space that GPT-4 learned during its pre-training phase.
Nice. Okay, beautiful. So, here we are. Nothing new that we learned now. There's no additional
training to GPT 3.5. We just optimize here the prompt to probe GPT 3.5, that we can get the best
out of GPT 3.5 without learning GPT 3.5, anything new. We are just trying to squeeze out the best
performance of GPT 3.5 or your open source LLM. If you have a 7 billion or 3 billion LLM,
this is interesting. Okay, but now let's come to the main study. You see June 11, 2024,
Stanford University, text grade, their automatic differentiation via text. And now we need
everything that we just learned today and we build on it and we will develop a new methodology.
So, again, let's come back here to autograd, the numerical calculation of back propagation here,
using numerical gradients in our network. And then they say we use now this analogon,
the same idea on different complexity levels on different objects. And as you can see here,
in this visualization, you can use it here, prompt for an LLM, a query for a search engine,
or tool prompt if you call specific tools. And yes, we are talking here about multi-AI agent system.
A little bit later, I will give you even more complex definition. And we have here an optimization circle that is happening. Beautiful. Again, I already showed you
here this kind of analogy in the abstraction space, either mathematically or in the PyTorch
notation or now in the complete new text grade code extension that you have to get familiar
yourself with the four officially Jupyter notebooks published by Stanford University,
Stanford University, which I highly recommend you have a look at. Now, the nice thing, since this is now, if you abstract it away from a pure prompt structure,
you can use this also for a molecule optimization if you do here an optimization by LLMs or vision
language models. And of course, you can use the same methodology for a better interaction of the
LLM now with a code LLM. And you have here code at the iteration T. And then here you have exactly
here this gradients that come back, that analyze it, that tries to improve the code here. And then
you have here the better code at iteration T plus one. So you see, you are depending now here on the
intelligence, let's say, of two LLM system or multi-LLM systems. If you think about, you can
make this in a network of LLMs. Great. But I would like to give you here an official example here
for prompt optimization that you get a feeling. How good is it? What is it? What's happening?
So we start with a prompt. Let's say you write this prompt and it says, hey, LLM, you will answer
a reasoning question. Think step by step. The last line of your response should be the following
format. Answer where value is a numerical value. And then you try this on, let's say,
GPD 3.5 or Mistral 7b or whatever open source you like, and you get an accuracy of 77%.
Great. Now, if you run through text, great. If you do this coding that I showed you before, notebooks,
the third notebook is exactly for this example, how to optimize this. And after it runs and runs
you will get now a better prompt, an automated programming prompt engineering.
And now the new prompt is as follows. You will answer a reasoning question. The same. But now,
list each item in its quantity in a clear and consistent format, such as item, quantity, sum
the values directly from the list and provide a concise summation. Ensure the final answer
is clearly indicated in this format. You give it a format where the value is a numerical value.
Then you go on, verify the relevance of each item to the context of the query and handle
potential errors or ambiguities in the input. Finally, double check the final count to ensure
accuracy. And with this particular prompt on the same GPD 3.5, you get now an accuracy of 92%.
Isn't that beautiful? So you see, the main task is not to learn something new to GPD 3.5,
to fine tune or to align it or to whatever extent its domain knowledge. No. It is here
a configuration of two or more LLMs to optimize the prompt structure for a given LLM. And we call
it, if you want a programming now, programming prompt engineering. So no hand optimization
of your prompt, because you can run this, I don't know, 100 times, 500 times, a thousand times,
and you get here for a specific model, the best way to do it. Now, as I showed you with the pseudo
code, you might like to have here on the left side here, the mathematical notation from the
numerical autograde operation. This is this one here. And on the right side, you have now the
verbal, how we do this now here, the implementation for the gradient operator. So you're familiar with
autograde. And now what we see now in this new methodology here is, hey, here's a conversation
with an LLM, some sentences, some dialogues, plus you say, here's the conversation. Below is
now the criticism of GPD 4 on particular parts in this conversation. And now explain how to improve
here that we get a better result, how to improve here the prompt structure, the prompt sequence,
or the prompt complexity itself, maybe include causal reasoning. So you see, however you like
to see it, this is the analogon that they stress here in their publication. Of course, it can be
a little bit more challenging, because you remember, in DSPy, we had those optimizers.
And here too, we have optimizers. And in the standard gradient descent, the autograde,
for example, the current value of the variable is combined here with the gradient through subtraction. So you have this simple mathematical operation. And now, updating this now, but not
in the numerical gradient descent, but now in the textual gradient descent, in our new library,
we have now the command textual gradient descent TGD step, and you can do this in a prompt.
So if you want to see this pseudocode implementation, you say, LLM, below are
the criticism of X, incorporate the criticism, and produce a new variable. And this variable
might be a subset for a better prompt optimization, or if you go to more complex systems,
I will show you in a minute. But please note, my green grasshoppers, depending on the complexity
level of this LLM, that it has been pre-trained on, and maybe you eliminate here the alignment
of the LLM, because you don't want here standardized predefined answers, but you need an LLM that is
really free quotation mark, to give you here also a harsh criticism. And given the causal reasoning
capability of this particular LLM, in our case, a GPT-4 and a GPT-3.5, or maybe easier, you have a
Mistral 7B and a Phi 3 Mini, you have to be really careful that you do not cross the threshold of
complexity level or causal reasoning threshold that one of the system is simply not able to perform.
And the one system, GPT-3.5, must still be able to understand the complex answer of GPT-4,
otherwise GPT-3.5 is lost. So after a week of experimenting with this, this is a real sensitive
equilibrium that you have to be careful if you go to more complex causal reasoning tasks.
Now I know that you want to see the performance benchmark between DSPy and TextGrad.
Okay, let's have a look at this. So now we optimize the system prompt for GPT-3.5 Turbo
using GPT-4 Omni as the gradient engine here that provides here the
analytic feedback during this textural back propagation. Beautiful. Let's start here with
object counting. So if we have here a chain of thought, zero shot, we get an accuracy of 77.8.
With DSPy, please notice, we have eight demonstration, we get 84.
And with TextGrad, with zero demonstration, we get close to 92%. Now word sorting, do the same,
chain of thought, zero shot, 76. DSPy with eight demonstration, 79.8. And TextGrad with zero
demonstration, identical to DSPy with eight demonstration. And the same is true for different
data set. So you see, even without any demonstration, TextGrad at least achieves
the same performance like DSPy, but with zero demonstration, which is really nice.
From the original literature, let me show you this. And again, they have here this analogon of the numerical optimization and of the automatic
differentiation. And with this beautiful TextGrad, it can be complex and potentially non-differentiable function where the domain and the codomain of the function can be unstructured
data. Yes, yes, yes. And they show us here a simple loss function for a code snippet. So if a code
LLM can be the following. So you have, if you want here, the loss function depending on the code and
your target goal that you want to achieve in the code optimization task. So for the LLM, this means, hey, here's your code snippet. This is the code. And here's the goal for this snippet,
whatever you want to achieve, faster, shorter, use another library, whatever. And then you evaluate
the snippet for the correctness and the runtime complexity, for example. And then the authors,
Stanford, specifies here where we can use this evaluation signal, this evaluation here,
to optimize the code snippet powered by the well-documented ability of LLMs to simulate
the human feedback, the ability of LLMs to self-evaluate, and the ability of LLMs to self-improve.
Now, I personally think we are not there yet to have a perfect, 100% accurate self-feedback,
self-evaluation capability, and a self-improvement capability of our LLMs today. And this includes
and a self-improvement capability of our LLMs today. And this includes GPT-4 Omni.
We have a lot of mistakes. Remember, the legal systems were one sort of old questions. We are
completely hallucinated and not based on facts. As long as we have this performance of LLM,
this self-feedback idea, the self-evaluate idea, and the self-improve idea, I handle with specific
care. And I do not trust those systems. Let me give you from a green grasshopper a very
simple explanation of what I just told you. Imagine we have here on the left-hand side an LLM. Let's
call it an evaluator LLM or a teacher LLM. It is GPT-4. And this GPT-4, let's say, can handle a
complexity level or causal reasoning level or logical deduction level of 6 out of 10. So really
good. And then we have here our API channel. And then we have here, let's say, Mistral 7b.
And Mistral 7b, complete level reaches only three complexity level out of 10. And now with this
methodology, our task is clear. We want a prompt optimization for this LLM Mistral 7b. So whatever
the model is capable today with this configuration, with this pre-training, with this fine tuning that
you have, you want to get the maximum out of this system. So you want to have the perfect prompt.
So you run 100 tests or 500 optimizations with this natural gradient descent methodology that
we have now in taxed grad. But careful, there is something like a complexity theorem.
You have to be careful that you can establish a useful and beneficial communication between those
two models. The moment GPT-4 outputs something for Mistral 7b that is too complicated in its
semantic structure for Mistral 7b with a complexity level of 3 to implement, all this self-feedback
and self-evaluate and self-improve fails completely. You have a hard interrupt here.
The system is not able to understand what it could do because maybe its self-reasoning capabilities
are not at all able to understand the input from GPT-4. There are some beautiful theorems here in
the complexity theory that you can take this further if you do not have just a prompt optimization,
but you have a system parameter optimization for designing new molecules in drug theory
or in biomedical or whatever. So you have to be really careful with this configuration of LLM
those systems. Let's make it very easy. Understand each other. And maybe I noticed if I dump down,
make it less complex the answer or the instruction here by GPT-4 for Mistral 7B.
Mistral 7b finds much faster the optimal prompt. So you see just a week so I'm not really able to
give you any further details because I'm just exploring this myself, but I will do a video a
little bit later on on more concrete examples. I can show you here a certain threshold in this idea.
Beautiful. As I told you we do not only are limited to prompt optimization
and to find here a system prompt because if you think that a system prompt is more or less just a parameter or maybe a hyperparameter for a system for an LLM, we can do another form of optimization
and the authors call it here an instance optimization. We directly treat a solution
to a problem code snippet or whatever or a molecule design as an optimization variable.
And this is the nice thing here. Like if we have a code instead of we would like to improve at
the time. So this now this new framework produces here the gradients for and directly optimizes
here the code variable. So you do not have to limit yourself to the prompt optimization,
but you can go for any optimization variable of the system if you can describe it and if the system
understands it and if the system has a causal reasoning ability to understand if you change
the molecular structure of a chemical compound, what would be the effect if the system this LLM
has been pre-trained here on enough biochemical or structural chemical pre-trained datasets.
So this now is in my domain science much more interesting than DSPy, but it has its own
limitations. Yeah, let's come to the result. Reasoning. Here the official table two from
the documentation by Stanford University solution optimization for zero short question
answering with GPT-4 Omni. You, there's this famous Google proof question and answer data set
and with a chain of thought GPT-4. So if we say hey restrict yourself to chain of thought we have an
accuracy of 50% and you might say what 50% that's it. Yes, this is it. If you look for the best
model you can imagine complex chain of thought, tree of thought, graph of thought combined with self-reflective
self-reflective and whatever you like we achieve today in June 2024 53.6% accuracy.
A little bit more than off. Now if we use tax grad I personally would have expected a better
performance but it is 55.0. These are the data. Now if you go here to different datasets that
are specific for reasoning and I showed you in my last video so you have comparable
performance data you see here the jump from TextGrad to a chain of thought is from 85.7 to 88.4
or 91 to 95. This is nice but not really as powerful as you would have expected but on
the other hand if you go from 91 to 95 this is great. So maybe dampen my expectation a little bit
and have a look at this. Yeah reasoning real easy you are immediately familiar if you look here the
example by Stanford the system prompt you have you treat this now as I told you as a variable
so the system prompt is now you simply hey you are helpful language model think step by step wow
and then you say here the rule description system prompt to the language model this is exactly what is your system prompt define and then you set up the model and you have here the black spark llm
where the system prompt is our defined system prompt and then as you know it from pytorch it
follows the same thing and this is the nice thing now we stand for the organs this is 80% here of
pytorch if you understood everything behind it yes if you're new to the system I looked at the
publication I said I don't understand a thing so you have an optimizer beautiful now you have this
functional textual gradient descent that you now understand what is the theory behind this
and then you go like you have normally you have your forward pass you perform the backward pass you compute the gradients and you update the system prompt it is logic it is what we know
and now we understand the theory behind this and you have a new library that you implement
beautiful open source great let's come here to the final insights here and let's stay with reasoning because I am interested
in the reasoning abilities of llm and the author stanford says hey as the paradigm of ai shifts
from training individual language model vision language model to optimizing now compound systems
involving multiple interacting language models vision language models robotics models
all those components and all this tool use that we have in multi-agent system
we need now a new generation of automated optimizers of the system to find here let's
say the best prompt when our multi llm or multi vLLMs system communicate so they are
continue their research for better automated optimizer but the optimizer here is already
really nice but of course the next step is a network of LLMs now textual combines here
the reasoning power of LLMs with the decomposition or efficiency of back propagation to optimize
the system but you see here the crucial word where it all hangs on is the reasoning ability
of LLMs and i find this so fascinating because you know just a week ago i showed you here two
videos about how you can improve the reasoning performance of LLMs by grokking and what it means
on how you do grokking LLMs for an increased performance so kind of the circle closes now
because if you want to increase the reasoning capabilities of LLMs grokking seems to be the way
to go and no it has nothing to do with Elon Musk or Groq Inc for this ultra fast
inference time this is a different effect that i showed you here in my two videos
yes beautiful so here you have it we have now starting from DSPy a self-improving machine
learning system from stanford now after a year maybe a little bit more than a year we have now
the next iteration the next new technology that is based on ds pi and on prodigy but now this new
but now this new tax grad system can do so much more and goes deeper test it out for your domain
knowledge for your specific task maybe your performance may be different to my experience
so do not trust anything you're here on the internet go try it out yourself you can use
here the free colab notebooks from stanford university but remember you have if you want to use GPT-4 omni you have to have an open e i key that you have maybe to pay or if we are new you
have i think five dollar free credits for you so you can try this out have a look at your particular
task in your domain and evaluate yourself is this new technology is as exciting as it was for me
to test it out now and i will go on and i will use tax grade for my next videos and i will show
you and i will implement this also in my systems and here we are i hope it was informative i hope
you enjoyed it a little bit and it would be great to see you in my next video
"""

from utils.summarizer import summarize
from utils.translator import translate_content
from dotenv import load_dotenv

load_dotenv()

model_name = 'gpt-3.5-turbo'
summary_length = 1000

summary_data = summarize(yt_transcript, model_name=model_name, summary_length=summary_length)
print(summary_data['final_summary'])

summaries = summary_data['summaries']
print(summaries)

translation_data = translate_content(summaries, target_language='de')
translations = translation_data['translations']

print(translations)