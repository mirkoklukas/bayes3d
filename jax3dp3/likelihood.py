import jax.numpy as jnp
import jax
import functools
from .utils import extract_2d_patches
from functools import partial

# @functools.partial(jax.jit, static_argnames=["r", "outlier_prob"])
def threedp3_likelihood_alternate(
    obs_xyz: jnp.ndarray,
    rendered_xyz: jnp.ndarray,
    r,
    outlier_prob
):
    obs_mask = obs_xyz[ :,:,2] > 0.0
    rendered_mask = rendered_xyz[:,:,2] > 0.0
    rendered_xyz_patches = extract_2d_patches(rendered_xyz, (5,5))
    counts = counts_per_pixel(
        obs_xyz,
        rendered_xyz_patches,
        r,
    )
    num_latent_points = rendered_mask.sum()
    probs = 1 / (((1 - outlier_prob)/num_latent_points) * 4/3 * jnp.pi * r**3) * counts + outlier_prob
    log_probs = jnp.log(probs)
    return jnp.sum(jnp.where(obs_mask, log_probs, 0.0))

@functools.partial(
    jnp.vectorize,
    signature='(m),(h,w,m)->()',
    excluded=(2,),
)
def counts_per_pixel(
    data_xyz: jnp.ndarray,
    model_xyz: jnp.ndarray,
    r: float,
):
    """    Args:
        data_xyz (jnp.ndarray): (3,)
            3d coordinate of observed point
        model_xyz : (filter_height, filter_width, 3),
        r : float, sphere radius
        outlier_prob: float
        num_latent_points: int
    """
    distance = jnp.linalg.norm(data_xyz - model_xyz, axis=-1).ravel() # (4,4)
    return jnp.sum(distance <= r)

@functools.partial(
    jnp.vectorize,
    signature='(m)->()',
    excluded=(1,2,3,4,),
)
def count_ii_jj(
    ij,
    data_xyz: jnp.ndarray,
    model_xyz: jnp.ndarray,
    r: float,
    filter_size: int
):
    t = data_xyz[ij[0], ij[1], :] - jax.lax.dynamic_slice(model_xyz, (ij[0], ij[1], 0), (2*filter_size + 1, 2*filter_size + 1, 4))
    distance = jnp.linalg.norm(t, axis=-1).ravel() # (4,4)
    return jnp.sum(distance <= r)


def threedp3_likelihood(
    obs_xyz: jnp.ndarray,
    rendered_xyz: jnp.ndarray,
    r,
    outlier_prob
):
    filter_size = 2
    obs_mask = obs_xyz[:,:,2] > 0.0
    rendered_mask = rendered_xyz[:,:,2] > 0.0
    rendered_xyz_padded = jax.lax.pad(rendered_xyz,  -100.0, ((filter_size,filter_size,0,),(filter_size,filter_size,0,),(0,0,0,)))
    jj, ii = jnp.meshgrid(jnp.arange(obs_xyz.shape[1]), jnp.arange(obs_xyz.shape[0]))
    indices = jnp.stack([ii,jj],axis=-1)
    counts = count_ii_jj(indices, obs_xyz, rendered_xyz_padded, r, filter_size)
    num_latent_points = rendered_mask.sum()
    probs = 1 / (((1 - outlier_prob)/num_latent_points) * 4/3 * jnp.pi * r**3) * counts + outlier_prob
    log_probs = jnp.log(probs)
    return jnp.sum(jnp.where(obs_mask, log_probs, 0.0))


def sample_coordinate_within_r(r, key, coord):
    phi = jax.random.uniform(key, minval=0.0, maxval=2*jnp.pi)
    
    new_key, subkey1, subkey2 = jax.random.split(key, 3)

    costheta = jax.random.uniform(subkey1, minval=-1.0, maxval=1.0)
    u = jax.random.uniform(subkey2, minval=0.0, maxval=1.0)

    theta = jnp.arccos(costheta)
    radius = r * jnp.cbrt(u)

    sx = radius * jnp.sin(theta)* jnp.cos(phi)
    sy = radius * jnp.sin(theta) * jnp.sin(phi)
    sz = radius * jnp.cos(theta)

    return new_key, coord + jnp.array([sx, sy, sz]) 

def sample_cloud_within_r(cloud, r):
    cloud_copy = cloud.reshape(-1, 3)  # reshape to ensure correct scan dimensions
    key = jax.random.PRNGKey(214)
    sample_coordinate_partial = partial(sample_coordinate_within_r, r)

    return jax.lax.scan(sample_coordinate_partial, key, cloud_copy)[-1]