/*
 * OpenControl for Pixel Buds Pro 2
 * Copyright (C) 2026 Ted Sluis
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
 * General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */
package io.github.tedsluis.opencontrolpixelbuds.domain

/**
 * Which Pixel Buds model the connected Buds are, and the features the app shows for it.
 *
 * The model is recognised from the firmware string the Buds announce (see `DeviceProfiles` in `:data`). It is not taken from the
 * Bluetooth name, which the user can change.
 *
 * Gen 1 support is not verified on hardware yet (`GEN1_SUPPORT_INVESTIGATION.md`), so it is read-only. Its feature set comes from
 * qzed/pbpctrl's Gen 1 proto (2022–2023) and is 🟡 until a Gen 1 capture confirms it:
 * - no Adaptive mode (pbpctrl added `ANC_STATE_ADAPTIVE` only in 2025, for the Pro 2);
 * - no head gestures (field 29) and no case sounds (fields 27/28), which pbpctrl never had.
 */
enum class BudsModel(
    val label: String,
    /** The noise-control modes this model has, in the on-screen order of the official Pro 2 app. */
    val ancModes: List<AncMode>,
    val hasHeadGestures: Boolean,
    val hasCaseSounds: Boolean,
) {
    PIXEL_BUDS_PRO_2(
        label = "Pixel Buds Pro 2",
        ancModes = listOf(AncMode.ACTIVE, AncMode.OFF, AncMode.ADAPTIVE, AncMode.TRANSPARENT),
        hasHeadGestures = true,
        hasCaseSounds = true,
    ),
    PIXEL_BUDS_PRO(
        label = "Pixel Buds Pro (1st generation)",
        ancModes = listOf(AncMode.ACTIVE, AncMode.OFF, AncMode.TRANSPARENT),
        hasHeadGestures = false,
        hasCaseSounds = false,
    ),
    ;

    fun hasAncMode(mode: AncMode): Boolean = mode in ancModes

    companion object {
        /** What the UI assumes before the model is known: today's (Pro 2) screens, unchanged. */
        val DEFAULT: BudsModel = PIXEL_BUDS_PRO_2
    }
}
