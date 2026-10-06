#version 330

// Vanilla 26.2 text.vsh + PandariaMc "/twitch rechts": GUI text whose vertex color is one of the marker colors
// (proxy:twitch ChatMarker - normal colors with blue moved one step, invisible to the eye) is moved to the right
// edge of the screen. Keep MARKERS in sync with ChatMarker.COLORS.

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:sample_lightmap.glsl>
#endif

#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
in ivec2 UV2;
#endif

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
uniform sampler2D Sampler2;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
#endif

out vec4 vertexColor;
out vec2 texCoord0;

#ifdef IS_GUI
const int MARKER_COUNT = 22;
const ivec3 MARKERS[MARKER_COUNT] = ivec3[](
    ivec3(255, 255, 254),
    ivec3(181, 186, 194),
    ivec3(114, 137, 219),
    ivec3(254, 231, 93),
    ivec3(237, 66, 70),
    ivec3(87, 242, 136),
    ivec3(145, 70, 254),
    ivec3(255, 0, 1),
    ivec3(0, 0, 254),
    ivec3(0, 128, 1),
    ivec3(178, 34, 35),
    ivec3(255, 127, 81),
    ivec3(154, 205, 51),
    ivec3(255, 69, 1),
    ivec3(46, 139, 88),
    ivec3(218, 165, 33),
    ivec3(210, 105, 31),
    ivec3(95, 158, 161),
    ivec3(30, 144, 254),
    ivec3(255, 105, 181),
    ivec3(138, 43, 227),
    ivec3(0, 255, 128)
);
// Default chat width (320 GUI px) + a small margin: marked lines end at the right edge with default chat settings.
const float CHAT_WIDTH = 324.0;

bool isMarked(vec3 color) {
    ivec3 rgb = ivec3(round(color * 255.0));
    for (int i = 0; i < MARKER_COUNT; i++) {
        if (rgb == MARKERS[i]) return true;
    }
    return false;
}
#endif

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * sample_lightmap(Sampler2, UV2);
#else
    vertexColor = Color;
#endif

#ifdef IS_GUI
    // GUI projection is orthographic: ProjMat[0][0] = 2 / gui width, so the screen is 2 / ProjMat[0][0] GUI px wide.
    if (isMarked(Color.rgb)) {
        float shift = 2.0 - CHAT_WIDTH * ProjMat[0][0];
        if (shift > 0.0) gl_Position.x += shift * gl_Position.w;
    }
#endif
    texCoord0 = UV0;
}
