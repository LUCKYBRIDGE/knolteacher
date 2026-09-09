using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Ink;
using System.Windows.Input;

namespace KnolTeacher.Desktop.Services;

/// <summary>
/// 자필 전자서명 보정 스타일
/// </summary>
public enum SignatureStyle
{
    /// <summary>
    /// 만년필 모드: 부드러운 입획·출획 테이퍼링 및 자연스러운 필압 (기본 권장)
    /// </summary>
    FountainPen,

    /// <summary>
    /// 붓펜 모드: 굵기 대비가 크고 풍부한 붓글씨 캘리그래피 터치
    /// </summary>
    BrushPen,

    /// <summary>
    /// 일반 펜: 보정 없는 기본 균일 굵기
    /// </summary>
    Standard
}

/// <summary>
/// 전자서명 획(Stroke) 입획·출획 테이퍼링, 손떨림 보정, 유기적 필압 처리 유틸리티
/// </summary>
public static class SignatureStrokeBeautifier
{
    /// <summary>
    /// 단일 획에 선택한 스타일의 붓터치 및 입출획 테이퍼링을 적용합니다.
    /// </summary>
    public static void BeautifyStroke(Stroke stroke, SignatureStyle style)
    {
        if (stroke == null || stroke.StylusPoints == null || stroke.StylusPoints.Count < 2)
            return;

        if (style == SignatureStyle.Standard)
        {
            stroke.DrawingAttributes.IgnorePressure = true;
            return;
        }

        var raw = stroke.StylusPoints;
        int n = raw.Count;

        // 1. 누적 이동 거리(Cumulative Distance) 계산
        double[] dist = new double[n];
        dist[0] = 0;
        for (int i = 1; i < n; i++)
        {
            double dx = raw[i].X - raw[i - 1].X;
            double dy = raw[i].Y - raw[i - 1].Y;
            dist[i] = dist[i - 1] + Math.Sqrt(dx * dx + dy * dy);
        }

        double totalLen = dist[n - 1];

        // 2. 5px 미만의 작은 점(마침표, 받침 점, 이응 획 등)은 원형 유지
        if (totalLen < 5.0)
        {
            stroke.DrawingAttributes.IgnorePressure = false;
            stroke.DrawingAttributes.FitToCurve = true;
            var dotPoints = new StylusPointCollection();
            foreach (var p in raw)
            {
                dotPoints.Add(new StylusPoint(p.X, p.Y, 0.50f));
            }
            stroke.StylusPoints = dotPoints;
            return;
        }

        // 3. 꺾임각 감지 (의도적인 날카로운 코너(75° 이상) 보존)
        bool[] isCorner = new bool[n];
        for (int i = 1; i < n - 1; i++)
        {
            double v1x = raw[i].X - raw[i - 1].X;
            double v1y = raw[i].Y - raw[i - 1].Y;
            double v2x = raw[i + 1].X - raw[i].X;
            double v2y = raw[i + 1].Y - raw[i].Y;
            double len1 = Math.Sqrt(v1x * v1x + v1y * v1y);
            double len2 = Math.Sqrt(v2x * v2x + v2y * v2y);
            if (len1 > 1.5 && len2 > 1.5)
            {
                double dot = (v1x * v2x + v1y * v2y) / (len1 * len2);
                if (dot < 0.25) // 코너 각도 약 75도 이상 꺾임
                {
                    isCorner[i] = true;
                }
            }
        }

        // 4. 점 밀도 재배치 (Resampling & Densification: 약 2.2px 간격)
        List<Point> sampled = new();
        double step = 2.2;
        double currentDist = 0;
        int segIdx = 0;

        while (currentDist <= totalLen)
        {
            while (segIdx < n - 2 && dist[segIdx + 1] < currentDist)
            {
                segIdx++;
            }

            double segLen = dist[segIdx + 1] - dist[segIdx];
            double t = segLen > 0.001 ? (currentDist - dist[segIdx]) / segLen : 0;
            t = Math.Max(0, Math.Min(1, t));

            double x = raw[segIdx].X + t * (raw[segIdx + 1].X - raw[segIdx].X);
            double y = raw[segIdx].Y + t * (raw[segIdx + 1].Y - raw[segIdx].Y);

            sampled.Add(new Point(x, y));
            currentDist += step;
        }

        // 마지막 정확한 지점 포함
        sampled.Add(new Point(raw[n - 1].X, raw[n - 1].Y));

        // 5. 부드러운 스플라인 이동평균 평활화 (손떨림 보정)
        int m = sampled.Count;
        Point[] smoothed = new Point[m];
        smoothed[0] = sampled[0];
        smoothed[m - 1] = sampled[m - 1];

        for (int i = 1; i < m - 1; i++)
        {
            smoothed[i] = new Point(
                0.22 * sampled[i - 1].X + 0.56 * sampled[i].X + 0.22 * sampled[i + 1].X,
                0.22 * sampled[i - 1].Y + 0.56 * sampled[i].Y + 0.22 * sampled[i + 1].Y
            );
        }

        // 평활화된 점들의 누적 거리 재계산
        double[] sDist = new double[m];
        sDist[0] = 0;
        for (int i = 1; i < m; i++)
        {
            double dx = smoothed[i].X - smoothed[i - 1].X;
            double dy = smoothed[i].Y - smoothed[i - 1].Y;
            sDist[i] = sDist[i - 1] + Math.Sqrt(dx * dx + dy * dy);
        }
        double smoothLen = sDist[m - 1];

        // 6. 스타일별 테이퍼링 파라미터 구성
        bool isBrush = style == SignatureStyle.BrushPen;
        float pStart = isBrush ? 0.05f : 0.08f;
        float pEnd = isBrush ? 0.015f : 0.03f;
        float pBase = isBrush ? 0.52f : 0.50f;

        double inLen = isBrush ? Math.Min(32.0, smoothLen * 0.30) : Math.Min(24.0, smoothLen * 0.25);
        double outLen = isBrush ? Math.Min(48.0, smoothLen * 0.40) : Math.Min(36.0, smoothLen * 0.35);

        // 짧은 획의 경우 입획과 출획이 겹치지 않도록 스케일 조정
        if (inLen + outLen > smoothLen)
        {
            double scale = smoothLen / (inLen + outLen);
            inLen *= scale;
            outLen *= scale;
        }

        var newPoints = new StylusPointCollection();

        for (int i = 0; i < m; i++)
        {
            double dFromStart = sDist[i];
            double dFromEnd = smoothLen - dFromStart;

            float p = pBase;

            // [입획] 테이퍼링: 서서히 굵어짐
            if (dFromStart < inLen && inLen > 0)
            {
                double u = dFromStart / inLen;
                double easeIn = Math.Sin(u * Math.PI * 0.5);
                p = (float)(pStart + (pBase - pStart) * easeIn);
            }

            // [출획] 테이퍼링: 서서히 가늘어짐
            if (dFromEnd < outLen && outLen > 0)
            {
                double v = dFromEnd / outLen;
                double easeOut = Math.Sin(v * Math.PI * 0.5);
                float pExit = (float)(pEnd + (pBase - pEnd) * easeOut);
                p = Math.Min(p, pExit);
            }

            // [몸체] 곡률 및 필압 보정 (커브 회전 시 잉크가 맺히는 자연스러운 표현)
            if (dFromStart >= inLen && dFromEnd >= outLen && i > 0 && i < m - 1)
            {
                double v1x = smoothed[i].X - smoothed[i - 1].X;
                double v1y = smoothed[i].Y - smoothed[i - 1].Y;
                double v2x = smoothed[i + 1].X - smoothed[i].X;
                double v2y = smoothed[i + 1].Y - smoothed[i].Y;
                double len1 = Math.Sqrt(v1x * v1x + v1y * v1y);
                double len2 = Math.Sqrt(v2x * v2x + v2y * v2y);

                if (len1 > 0.1 && len2 > 0.1)
                {
                    double cosA = Math.Max(-1.0, Math.Min(1.0, (v1x * v2x + v1y * v2y) / (len1 * len2)));
                    if (cosA < 0.95)
                    {
                        double curveBonus = (1.0 - cosA) * (isBrush ? 0.18 : 0.10);
                        p = Math.Min(0.70f, p + (float)curveBonus);
                    }
                }
            }

            newPoints.Add(new StylusPoint(smoothed[i].X, smoothed[i].Y, p));
        }

        // 7. [마감 보정] 끝점 날림(Flick) 미세 꼬리 연장으로 뭉툭한 원형 캡 완전 제거
        if (m >= 2 && outLen > 8.0)
        {
            double endDx = smoothed[m - 1].X - smoothed[m - 2].X;
            double endDy = smoothed[m - 1].Y - smoothed[m - 2].Y;
            double endLen = Math.Sqrt(endDx * endDx + endDy * endDy);
            if (endLen > 0.4)
            {
                double flickDist = isBrush ? 2.5 : 1.6;
                double flickX = smoothed[m - 1].X + (endDx / endLen) * flickDist;
                double flickY = smoothed[m - 1].Y + (endDy / endLen) * flickDist;
                newPoints.Add(new StylusPoint(flickX, flickY, 0.015f));
            }
        }

        stroke.DrawingAttributes.IgnorePressure = false;
        stroke.DrawingAttributes.FitToCurve = true;
        stroke.StylusPoints = newPoints;
    }

    /// <summary>
    /// 컬렉션 내 모든 획을 일괄 보정합니다.
    /// </summary>
    public static void BeautifyAll(StrokeCollection strokes, SignatureStyle style)
    {
        if (strokes == null) return;
        foreach (var s in strokes)
        {
            BeautifyStroke(s, style);
        }
    }
}
