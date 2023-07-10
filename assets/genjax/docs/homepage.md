# Overview

**GenJAX: a probabilistic programming library designed to scale probabilistic modeling and inference into high performance settings.** (1)
{ .annotate }

1.  Here, _high performance_ means massively parallel, either cores or devices.

    For those whom this overview page may be irrelevant: the value proposition is about putting expressive models and customizable Bayesian inference on GPUs, TPUs, etc - without sacrificing abstraction or modularity.

---

[**Gen**][gen] is a multi-paradigm (generative, differentiable, incremental) system for probabilistic programming. **GenJAX** is an implementation of Gen on top of [**JAX**][jax] (2) - exposing the ability to programmatically construct and manipulate **generative functions** (1) (computational objects which represent probability measures over structured sample spaces), with compilation to native devices, accelerators, and other parallel fabrics. 
{ .annotate }

1.  By design, generative functions expose a concise interface for expressing approximate and differentiable inference algorithms. 

    The set of generative functions is extensible! You can implement your own - allowing advanced users to performance optimize their critical modeling/inference code paths.

    You can (and we, at the [MIT Probabilistic Computing Project](http://probcomp.csail.mit.edu/), do!) use these objects for machine learning - including robotics, natural language processing, reasoning about agents, and modelling / creating systems which exhibit human-like reasoning.

    A precise mathematical formulation of generative functions is given in [Marco Cusumano-Towner's PhD thesis][marco_thesis].

2.  If the usage of JAX is not a dead giveaway, GenJAX is written in Python.

<div class="grid cards" markdown>

=== "Model code"
   
    <p align="center">
    Defining a beta-bernoulli process model as a generative function in GenJAX.
    </p>

    ```py linenums="1"
    @genjax.gen
    def model():
      p = beta(0, 1) @ "p"
      v = bernoulli(p) @ "v"
      return v
    ```


===   "Inference code"
    
    <p align="center">
    This works for **any** generative function, not just the beta-bernoulli model.
    </p>
    
    ```py linenums="1"
    def importance_sampling(
        key: PRNGKey,
        gen_fn: GenerativeFunction,
        model_args: Tuple,
        obs: ChoiceMap,
        n_samples: Int,
    ): # (1)!

        key, sub_keys = genjax.slash(key, n_samples)  # split keys
        _, (lws, trs) = jax.vmap(
            gen_fn.importance, # (2)!
            in_axes=(0, None, None),
        )(sub_keys, obs, args)
        log_total_weight = jax.scipy.special.logsumexp(lws)
        log_normalized_weights = lws - log_total_weight
        log_ml_estimate = log_total_weight - jnp.log(self.num_particles)
        return key, (trs, log_normalized_weights, log_ml_estimate)
    ```

    1.  Here's a few notes about the signature:
        * `PRNGKey` is the type of `jax.random.PRNGKey`. In GenJAX, we pass keys into generative code, and generative code returns a changed key.
        * `GenerativeFunction` refers to generative functions, objects which expose Gen's probabilistic interface.
        * For now, think of `ChoiceMap` as the type of object which Gen uses to express conditioning.

    2. `gen_fn.importance` is a _generative function interface_ method. Generative functions are responsible for implementing this method, to support conditional sampling and conditional density estimation. You can learn a lot more about this method in [the generative function interface](genjax/library/core/generative.md#generative-functions).
</div>

## What sort of things do you use GenJAX for?

<div class="grid cards" markdown>

=== "Real time object tracking"
    Real time tracking of objects in 3D using probabilistic rendering. (Left) Ground truth, (center) depth mask, (right) inference overlaid on ground truth.

    <p align="center">
    <img width="450px" src="./assets/gif/cube_tracking_inference_enum.gif"/>
    </p>

</div>

## Why Gen?

GenJAX is a [Gen][gen] implementation. If you're considering using GenJAX - it's worth starting by understanding what problems Gen purports to solve.

### The evolution of probabilistic programming languages

Probabilistic modeling and inference is hard: understanding a domain well enough to construct a probabilistic model in the Bayesian paradigm is challenging, and that's half the battle - the other half is designing effective inference algorithms to probe the implications of the model (1).
{ .annotate }

1.  Some probabilistic programming languages restrict the set of allowable models, providing (in return) efficient (often, exact) inference. 

    Gen considers a wide class of models - include Bayesian nonparametrics, open-universe models, and models over rich structures (like programs!) - which don't natively support efficient exact inference.

Model writers have historically considered the following design loop.

``` mermaid
graph LR
  A[Design model.] --> B[Implement inference by hand.];
  B --> C[Model + inference okay?];
  C --> D[Happy.];
  C --> A;
```

The first generation (1) of probabilistic programming systems introduced inference engines which could operate abstractly over many different models, without requiring the programmer to return and tweak their inference code. The utopia envisioned by these systems is shown below.
{ .annotate }

1.  Here, the definition of "first generation" includes systems like JAGS, BUGS, BLOG, IBAL, Church, Infer.NET, Figaro, Stan, amongst others.

    But more precisely, many systems preceded the [DARPA PPAML project][ppaml] - which gave rise to several novel systems, including the predecessors of Gen.

``` mermaid
graph LR
  A[Design model.] --> D[Model + inference okay?];
  B[Inference engine.] ---> D;
  D --> E[Happy.];
  D ---> A;
```

The problem with this utopia is that we often need to customize our inference algorithms (1) to achieve maximum performance, with respect to accuracy as well as runtime (2). First generation systems were not designed with this in mind.
{.annotate}

1.  Here, _programmable inference_ denotes using a custom proposal distribution in importance sampling, or a custom variational family for variational inference, or even a custom kernel in Markov chain Monte Carlo.
2.  _Composition_ of inference programs can also be highly desirable when performing inference in complex models, or designing a probabilistic application from several modeling and inference components. The first examples of universal inference engines ignored this design problem.

### Programmable inference

A worthy design goal is to allow users to customize when required, while retaining the rapid model/inference iteration properties explored by first generation systems.

Gen addresses this goal by introducing a separation between modeling and inference code: **the generative function interface**.

<p align="center">
<img width="800px" src="./assets/img/gen-architecture.png"/>
</p>

The interface provides an abstraction layer that inference algorithms can call to compute the necessary (_and hard to get right_!) math (1). Probabilistic application developers can also extend the interface to new modeling languages - and immediately gain access to advanced inference procedures.
{ .annotate }

1.  Examples of hard-to-get-right math: importance weights, accept reject ratios, and gradient estimators. 

    For simple models and inference, one might painlessly derive these quantities. As soon as the model/inference gets complicated, however, you might find yourself thanking the interface.

## Whose using Gen?

Gen supports a growing list of users, with collaboration across academic research labs and industry affiliates.

<p align="center">
<img width="450px" src="./assets/img/gen-users.png"/>
</p>

We're looking to expand our user base! If you're interested, [please contact us to get involved][probcomp_contact_form].

[gen]: https://www.gen.dev/
[gen.jl]: https://github.com/probcomp/Gen.jl
[genjax]: https://github.com/probcomp/genjax
[jax]: https://github.com/google/jax
[marco_thesis]: https://www.mct.dev/assets/mct-thesis.pdf
[ppaml]: https://www.darpa.mil/program/probabilistic-programming-for-advancing-machine-learning
[probcomp]: http://probcomp.csail.mit.edu/
[probcomp_contact_form]: https://docs.google.com/forms/d/e/1FAIpQLSfbPY5e0KMVEFg7tjVUsOsKy5tWV9Moml3dPkDPXvP8-TSMNA/viewform?usp=sf_link
