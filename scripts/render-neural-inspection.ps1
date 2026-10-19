param(
    [Parameter(Mandatory = $true)][string]$ReportPath,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [double]$ViewAngle = 0
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$report = Get-Content -LiteralPath $ReportPath -Raw | ConvertFrom-Json
if ($report.format -ne 'signa-madis-133-v1' -or -not $report.projections.Count) {
    throw 'Use the inspection report of an actual MaDiS inference output.'
}
$width = 1440; $height = 1050; $panelWidth = 480; $panelHeight = 310
$angle = $ViewAngle * [Math]::PI / 180
$cosine = [Math]::Cos($angle); $sine = [Math]::Sin($angle)
$horizontal = [System.Collections.Generic.List[double]]::new()
$vertical = [System.Collections.Generic.List[double]]::new()
foreach ($sample in $report.projections) {
    foreach ($property in $sample.joints.PSObject.Properties) {
        $point = $property.Value
        $horizontal.Add($point[0] * $cosine + $point[2] * $sine)
        $vertical.Add($point[1])
    }
}
$minX = ($horizontal | Measure-Object -Minimum).Minimum - .10
$maxX = ($horizontal | Measure-Object -Maximum).Maximum + .10
$minY = ($vertical | Measure-Object -Minimum).Minimum - .10
$maxY = ($vertical | Measure-Object -Maximum).Maximum + .10
$plotScale = [Math]::Min(($panelWidth - 65) / [Math]::Max(.1, $maxX - $minX), ($panelHeight - 45) / [Math]::Max(.1, $maxY - $minY))
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$background = [System.Drawing.Color]::FromArgb(16, 21, 37)
$foreground = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(232, 237, 248))
$muted = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(153, 166, 192))
$leftPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(84, 214, 221), 2)
$rightPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 165, 129), 2)
$bodyPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(171, 151, 246), 3)
$gridPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(45, 54, 75), 1)
$titleFont = New-Object System.Drawing.Font('Segoe UI', 20, [System.Drawing.FontStyle]::Bold)
$labelFont = New-Object System.Drawing.Font('Segoe UI', 12)
try {
    $graphics.Clear($background)
    $graphics.DrawString('Actual MaDiS output: retargeted skeleton', $titleFont, $foreground, 25, 16)
    $graphics.DrawString("$($report.frames) frames at $($report.fps) fps; view $ViewAngle degrees. Technical projection only; ASL meaning and handshape require validation.", $labelFont, $muted, 25, 56)
    for ($panel = 0; $panel -lt [Math]::Min(9, $report.projections.Count); $panel++) {
        $sample = $report.projections[$panel]
        $originX = ($panel % 3) * $panelWidth
        $originY = 100 + [Math]::Floor($panel / 3) * $panelHeight
        $graphics.DrawRectangle($gridPen, $originX + 8, $originY, $panelWidth - 16, $panelHeight - 8)
        $graphics.DrawString(('frame {0} / {1:N2} s' -f $sample.frame, $sample.time), $labelFont, $muted, $originX + 20, $originY + 10)
        $projected = @{}
        foreach ($property in $sample.joints.PSObject.Properties) {
            $point = $property.Value
            $x = $point[0] * $cosine + $point[2] * $sine
            $projected[$property.Name] = New-Object System.Drawing.PointF(
                ($originX + $panelWidth / 2 + ($x - ($minX + $maxX) / 2) * $plotScale),
                ($originY + 35 + ($maxY - $point[1]) * $plotScale)
            )
        }
        foreach ($pair in @(@('head', 'neck_01'), @('neck_01', 'clavicle_l'), @('neck_01', 'clavicle_r'))) {
            $graphics.DrawLine($bodyPen, $projected[$pair[0]], $projected[$pair[1]])
        }
        foreach ($side in @('l', 'r')) {
            $pen = if ($side -eq 'l') { $leftPen } else { $rightPen }
            foreach ($pair in @(@("clavicle_$side", "upperarm_$side"), @("upperarm_$side", "lowerarm_$side"), @("lowerarm_$side", "hand_$side"))) {
                $graphics.DrawLine($pen, $projected[$pair[0]], $projected[$pair[1]])
            }
            foreach ($finger in @('thumb', 'index', 'middle', 'ring', 'pinky')) {
                $previous = "hand_$side"
                for ($joint = 1; $joint -le 3; $joint++) {
                    $current = '{0}_0{1}_{2}' -f $finger, $joint, $side
                    $graphics.DrawLine($pen, $projected[$previous], $projected[$current])
                    $previous = $current
                }
            }
        }
        foreach ($point in $projected.Values) { $graphics.FillEllipse($foreground, $point.X - 2, $point.Y - 2, 4, 4) }
    }
    $graphics.DrawString('Cyan: anatomical left. Coral: anatomical right. Finger mean offsets and facial expressions are not recovered by this asset-free retarget.', $labelFont, $muted, 25, 1020)
    $bitmap.Save([System.IO.Path]::GetFullPath($OutputPath), [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    foreach ($resource in @($graphics, $bitmap, $foreground, $muted, $leftPen, $rightPen, $bodyPen, $gridPen, $titleFont, $labelFont)) { $resource.Dispose() }
}
Write-Output ([System.IO.Path]::GetFullPath($OutputPath))
