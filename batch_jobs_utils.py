import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import blf


# ——————————————————————————————————————————————————————————————————————
# MARK: HELPER CLASSES
# ——————————————————————————————————————————————————————————————————————


class BatchModal:  # MARK: BatchModal
    """A helper class for batch operations with loading bar, image preview and status message"""

    data_to_empty = []
    interval_seconds = 1.0

    overlay_area_type = "VIEW_3D"

    key_instructions = "'Esc' to cancel, 'Return' to conclude"
    progress_message = ""
    draw_overlay_text = True

    progress_color = (0.0, 0.5, 0.5)

    image: bpy.types.Image = None

    use_props_dialog = False

    # NOTE: These should not have to be touched
    _timer = None
    _start_count = 0
    _progress = 0.0

    _overlay_area = None
    _overlay_space_type = None
    _overlay_draw_handler = None

    def collection_names(self, context, edit_text):  # (Optional) Use for the 'search' parameter in StringProperty
        collections = bpy.data.collections
        return [c.name for c in collections]

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        wm = context.window_manager
        self._overlay_area = next(a for a in context.screen.areas if a.type == self.overlay_area_type)

        if self.use_props_dialog:
            return wm.invoke_props_dialog(self)
        return self.execute(context)

    def warmup(self, context: bpy.types.Context) -> None:
        """Initialises the necessary environment or resources to perform the batch operation."""
        self.progress_message = "Warming up"

        # self.data_to_empty = <list of data>

        # self.image = <Image>

        # <context variables>
        ...
        return None

    def execute(self, context: bpy.types.Context) -> set[str]:  # MARK: Execute
        wm = context.window_manager
        self.warmup(context)

        self.data_to_empty = self.data_to_empty[:]
        self._start_count = len(self.data_to_empty)

        self._overlay_space_type = type(self._overlay_area.spaces[0])
        self._draw_handler = self._overlay_space_type.draw_handler_add(self.draw_overlay, (), "WINDOW", "POST_PIXEL")
        self._timer = wm.event_timer_add(self.interval_seconds, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def main_process(self, context: bpy.types.Context, datablock) -> None:
        """Processes the first datablock in the list until the list is empty."""
        ...
        return None

    def undo_everything(self, context: bpy.types.Context) -> None:
        """Performs every necessary undo step to reset everything to its original state."""
        ...
        return None

    def cleanup(self, context: bpy.types.Context) -> None:
        """Performs any finalising steps to complete the batch operation."""
        ...
        return None

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:  # MARK: Modal
        wm = context.window_manager
        if event.type == "TIMER":
            self.main_process(context, self.data_to_empty[0])
            self.data_to_empty.pop(0)
            self._progress = 1.0 - len(self.data_to_empty) / self._start_count
            self._overlay_area.tag_redraw()

            if len(self.data_to_empty) < 1:
                self.cleanup(context)
                self._overlay_space_type.draw_handler_remove(self._draw_handler, "WINDOW")
                wm.event_timer_remove(self._timer)
                return {"FINISHED"}

        if event.type == "RET":
            self.cleanup(context)
            self._overlay_space_type.draw_handler_remove(self._draw_handler, "WINDOW")
            wm.event_timer_remove(self._timer)
            return {"FINISHED"}

        if event.type == "ESC":
            self.undo_everything(context)
            self._overlay_space_type.draw_handler_remove(self._draw_handler, "WINDOW")
            wm.event_timer_remove(self._timer)
            return {"CANCELLED"}
        return {"RUNNING_MODAL"}

    def draw_overlay(self) -> None:  # MARK: Overlay
        def rectangle(left_bottom: tuple[int, int], right_top: tuple[int, int]):
            vertices = [left_bottom, (left_bottom[0], right_top[1]), right_top, (right_top[0], left_bottom[1])]
            indices = [(0, 1, 2), (2, 3, 0)]
            return vertices, indices

        # Loading bar
        vertices, indices = rectangle((0, 10), (self._overlay_area.width * self._progress, 20))

        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        batch = batch_for_shader(shader, "TRIS", {"pos": vertices}, indices=indices)
        shader.bind()

        r, g, b = self.progress_color
        shader.uniform_float("color", (r, g, b, 1.0))

        batch.draw(shader)

        # Image
        if self.draw_overlay_text:
            font_id = 0
            blf.color(font_id, 1.0, 1.0, 1.0, 1.0)

            blf.size(font_id, 15.0)
            blf.position(font_id, 20, 30, 0)
            blf.draw(font_id, f"{self.key_instructions}: {self.bl_idname}: {self.progress_message}")

            blf.size(font_id, 20.0)
            blf.position(font_id, 20, 50, 0)
            blf.draw(font_id, f"{int(self._progress * 100)}%")

        # Text
        if self.image is not None:
            size = min(self._overlay_area.width * 0.5, self._overlay_area.height - 160)
            left = self._overlay_area.width / 2 - size / 2
            right = self._overlay_area.width / 2 + size / 2
            vertices, indices = rectangle((left, 80), (right, 80 + size))

            shader = gpu.shader.from_builtin("IMAGE")
            batch = batch_for_shader(
                shader, "TRIS", {"pos": vertices, "texCoord": ((0, 0), (0, 1), (1, 1), (1, 0))}, indices=indices
            )
            shader.bind()

            texture = gpu.texture.from_image(self.image)
            shader.uniform_sampler("image", texture)

            batch.draw(shader)
        return None
