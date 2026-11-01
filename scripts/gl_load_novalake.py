#!/usr/bin/env python3
# gl_load_novalake.py - headless OpenGL load on the NovaLake-S iGPU via Mesa (iris)
# Renders a heavy fragment shader into an off-screen 4K framebuffer for N seconds.
# Usage:  python3 gl_load_novalake.py [seconds]      (default 30)
import os, sys, time

os.environ.setdefault("INTEL_FORCE_PROBE", "d740")   # Mesa force-probe for d740
os.environ.setdefault("EGL_PLATFORM", "surfaceless") # no monitor / X needed
os.environ.pop("DISPLAY", None)                      # ignore MobaXterm X11 forwarding

import moderngl

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
W, H = 3840, 2160

print(" ********************************************************** ")
print(" ** Creating headless OpenGL context (EGL surfaceless)   ** ")
print(" ********************************************************** ")
ctx = moderngl.create_context(standalone=True, backend="egl",
                              libgl="libGL.so.1", libegl="libEGL.so.1")
print("GL_RENDERER :", ctx.info["GL_RENDERER"])
print("GL_VERSION  :", ctx.info["GL_VERSION"])
if "llvmpipe" in ctx.info["GL_RENDERER"].lower():
    print(" !! Running on llvmpipe (CPU), NOT the iGPU - check INTEL_FORCE_PROBE / Mesa !!")

prog = ctx.program(
    vertex_shader="""
        #version 330
        in vec2 in_pos;
        void main() { gl_Position = vec4(in_pos, 0.0, 1.0); }
    """,
    fragment_shader="""
        #version 330
        uniform float t;
        out vec4 color;
        void main() {
            vec2 p = gl_FragCoord.xy * 0.001;
            float v = 0.0;
            for (int i = 0; i < 200; i++) {          // heavy per-pixel math
                v += sin(p.x * float(i) + t) * cos(p.y * float(i) - t);
                p = p.yx * 1.0001 + 0.01;
            }
            color = vec4(fract(v), fract(v * 0.5), fract(v * 0.25), 1.0);
        }
    """,
)
vbo = ctx.buffer(bytes(__import__("array").array("f", [-1, -1, 3, -1, -1, 3])))
vao = ctx.simple_vertex_array(prog, vbo, "in_pos")
fbo = ctx.simple_framebuffer((W, H))
fbo.use()

print(" ********************************************************** ")
print(f" ** Rendering {W}x{H} frames for {DUR:.0f} s - watch gputop (rcs) ** ")
print(" ********************************************************** ")
frames, start, last = 0, time.time(), time.time()
while time.time() - start < DUR:
    prog["t"].value = time.time() - start
    vao.render()
    ctx.finish()                       # wait for the GPU so timing is real
    frames += 1
    now = time.time()
    if now - last >= 1.0:
        print(f"t={now - start:5.1f}s  frames={frames:6d}  avg FPS={frames / (now - start):7.2f}")
        last = now

el = time.time() - start
print(" ********************************************************** ")
print(f" ** RESULT: {frames} frames in {el:.1f} s = {frames / el:.2f} FPS at {W}x{H} ")
print(" ********************************************************** ")
