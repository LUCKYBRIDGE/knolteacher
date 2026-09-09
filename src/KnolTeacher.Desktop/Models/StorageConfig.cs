namespace KnolTeacher.Desktop.Models;

public class StorageConfig
{
    /// <summary>
    /// 사용자가 사전 설정한 기본 저장 디렉터리 경로 (비어있으면 기본 다운로드 폴더 사용)
    /// </summary>
    public string DefaultSaveDirectory { get; set; } = string.Empty;

    /// <summary>
    /// 판서 캡처 저장 시 기본 디렉터리 내 '놀티쳐_판서' 서브폴더 생성 여부 (기본: true)
    /// </summary>
    public bool CreateSubfolderForDrawings { get; set; } = true;
}
