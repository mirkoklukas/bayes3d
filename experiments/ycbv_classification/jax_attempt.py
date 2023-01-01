import trimesh
import time
import os
import numpy as np
import jax.numpy as jnp
import jax
import torch

import jax3dp3
import jax3dp3.utils
import jax3dp3.camera
import jax3dp3.nvdiffrast.common as dr
import jax3dp3.viz
import jax3dp3.transforms_3d as t3d
import jax3dp3.distributions
import jax3dp3.enumerations
import jax.dlpack
import jax3dp3.likelihood

h, w = 120, 160
fx,fy = 200.0, 200.0
cx,cy = 80.0, 60.0
near=0.01
far=50.0
max_depth=2.0
proj_list = list(jax3dp3.camera.open_gl_projection_matrix(h, w, fx, fy, cx, cy, near, far).reshape(-1))

model_names = os.listdir("/home/nishadgothoskar/jax3dp3/assets/models/")

glenv = dr.RasterizeGLContext(h, w, output_db=False)

for model in model_names:
    mesh = trimesh.load(os.path.join(jax3dp3.utils.get_assets_dir(),"models/{}/textured_simple.obj".format(model)))
    # mesh = trimesh.load(os.path.join(jax3dp3.utils.get_assets_dir(),"cube.obj"))
    vertices = np.array(mesh.vertices)
    vertices = np.concatenate([vertices, np.ones((*vertices.shape[:-1],1))],axis=-1)
    triangles = np.array(mesh.faces)
    dr.load_vertices(glenv, torch.tensor(vertices.astype("f"), device='cuda'), torch.tensor(triangles.astype(np.int32), device='cuda'),h, w)

gt_model_idx = 5
gt_mesh_name = model_names[gt_model_idx]
obs_image = jnp.zeros((h,w,4))
dr.load_obs_image(glenv, torch.tensor(np.array(obs_image).astype("f"), device='cuda'))

center_of_sampling = t3d.transform_from_pos(jnp.array([0.0, 0.0, 0.5]))
variance = 0.0000001
concentration = 0.01
key = jax.random.PRNGKey(10)
sampler_jit = jax.jit(jax3dp3.distributions.gaussian_vmf_sample)
gt_pose = sampler_jit(key, center_of_sampling, variance, concentration)
gt_pose_torch = torch.tensor(np.array(gt_pose), device='cuda')
gt_image = dr.rasterize(glenv, gt_pose_torch[None, ...], proj_list, h,w, gt_model_idx)[0]
gt_image_jnp = jnp.array(gt_image.cpu().numpy())


jax3dp3.viz.save_depth_image(gt_image[:,:,2].cpu(), "gt_image.png", max=max_depth)
dr.load_obs_image(glenv, gt_image)


r = 0.05
outlier_prob = 0.1
def scorer(rendered_image, gt):
    weight = jax3dp3.likelihood.threedp3_likelihood(gt, rendered_image, r, outlier_prob)
    return weight
scorer_parallel = jax.vmap(scorer, in_axes=(0, None))
scorer_parallel_jit = jax.jit(scorer_parallel)

import jax3dp3.bbox
non_zero_points = gt_image_jnp[gt_image_jnp[:,:,2]>0,:3]
_, centroid_pose = jax3dp3.bbox.axis_aligned_bounding_box(non_zero_points)
rotation_deltas = jax3dp3.enumerations.make_rotation_grid_enumeration(50, 20)
poses_to_score = jnp.einsum("ij,ajk->aik", centroid_pose, rotation_deltas)
poses_to_score_torch = torch.tensor(np.array(poses_to_score), device='cuda')


start= time.time()
all_scores = []

for (idx,model) in enumerate(model_names):
    images = jax.dlpack.from_dlpack(torch.utils.dlpack.to_dlpack(dr.rasterize(glenv, poses_to_score_torch, proj_list, h,w, idx)))
    weights = scorer_parallel_jit(images, gt_image_jnp)
    jax3dp3.viz.save_depth_image(images[weights.argmax(),:,:,2], "best_{}.png".format(model), max=max_depth)
    all_scores.append(weights.max())
end = time.time()
print ("Time elapsed:", end - start)
print(gt_mesh_name)
print(model_names[np.argmax(all_scores)])



from IPython import embed; embed()

print(np.array(model_names)[np.argsort(np.array(all_scores))])
