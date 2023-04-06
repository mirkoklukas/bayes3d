import jax3dp3 as j
import os
import jax.numpy as jnp
import jax
import matplotlib.pyplot as plt
from PIL import Image
import io
import numpy as np

intrinsics = j.Intrinsics(
    height=150,
    width=150,
    fx=200.0, fy=200.0,
    cx=75.0, cy=75.0,
    near=1.0, far=1000.0
)

plane = j.mesh.make_cuboid_mesh([1000.0, 1000.0, 0.001])
wall_pose = j.t3d.transform_from_pos(jnp.array([0.0, 0.0, 800.0]))

model_dir = os.path.join(j.utils.get_assets_dir(), "bop/ycbv/models")




renderer = j.Renderer(intrinsics)
renderer.add_mesh(plane)
model_names = j.ycb_loader.MODEL_NAMES
for IDX in range(len(model_names)):
    mesh_path_ply = os.path.join(model_dir,"obj_" + "{}".format(IDX+1).rjust(6, '0') + ".ply")
    mesh = j.mesh.load_mesh(mesh_path_ply)
    renderer.add_mesh(mesh)

object_pose = j.distributions.gaussian_vmf_sample(
    jax.random.PRNGKey(2),
    j.t3d.transform_from_pos(
        jnp.array([0.0, 0.0, 300.0])
    ),
    0.01, 0.1
)

GT_ID = 4
observed_image = renderer.render_multiobject(
    jnp.array([object_pose, wall_pose]),
    [GT_ID, 0]
)
j.get_depth_image(observed_image[:,:,2],max=intrinsics.far).save("gt.png")





object_pose_noisier = j.distributions.gaussian_vmf_sample(
    jax.random.PRNGKey(9),
    object_pose,
    3.0, 400.0
)

rendered = renderer.render_multiobject(
    jnp.array([object_pose_noisy, wall_pose]),
    [GT_ID+1, 0]
)


likelihood_outlier_parallel_jit = jax.jit(
    jax.vmap(jax.vmap(j.threedp3_likelihood, in_axes=(None, None, None, 0, None)), in_axes=(None, None, 0, None, None))
)

j.vstack_images(
    [
        j.get_depth_image(observed_image[:,:,2], max=intrinsics.far),
        j.get_depth_image(rendered[:,:,2], max=intrinsics.far)
    ]
).save("data.png")

# likelihood_r = jax.jit(
#     jax.vmap(j.gaussian_mixture_image, in_axes=(None, None, 0))
# )


OUTLIER_PROBS = jnp.linspace(0.1, 0.2, 100)
R = jnp.linspace(0.01, 0.1, 100)
OUTLIER_VOLUME = 1000000000.0

p = likelihood_outlier_parallel_jit(observed_image, rendered, R, OUTLIER_PROBS, OUTLIER_VOLUME)
norm_p = j.utils.normalize_log_scores(p)

plt.clf()
for i in range(len(R)):
    plt.plot(OUTLIER_PROBS,j.utils.normalize_log_scores(p[i]).reshape(-1))
plt.tight_layout()
plt.savefig("1.png")


plt.clf()
plt.matshow(norm_p)
plt.xlabel("outlier prob")
plt.ylabel("R")
plt.colorbar()
plt.tight_layout()
plt.savefig("1.png")

from IPython import embed; embed()




